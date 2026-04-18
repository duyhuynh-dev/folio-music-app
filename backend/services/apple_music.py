"""Apple Music Search API client."""

from __future__ import annotations

import os
import time
from pathlib import Path
from urllib.parse import quote_plus

import httpx
from jose import jwt
from pydantic import BaseModel


class AppleMusicTrack(BaseModel):
    id: str
    name: str
    artist: str
    preview_url: str | None = None
    apple_music_url: str | None = None


class AppleMusicClient:
    def __init__(
        self,
        storefront: str = "us",
        music_user_token: str | None = None,
    ) -> None:
        self.storefront = storefront
        self.music_user_token = music_user_token
        self.team_id = os.getenv("APPLE_MUSIC_TEAM_ID")
        self.key_id = os.getenv("APPLE_MUSIC_KEY_ID")
        self.private_key_path = os.getenv("APPLE_MUSIC_PRIVATE_KEY_PATH")

    def _build_developer_token(self) -> str:
        if not self.team_id or not self.key_id or not self.private_key_path:
            raise RuntimeError(
                "Apple Music env vars are missing. "
                "Set APPLE_MUSIC_TEAM_ID, APPLE_MUSIC_KEY_ID, APPLE_MUSIC_PRIVATE_KEY_PATH."
            )
        private_key = Path(self.private_key_path).read_text(encoding="utf-8")
        now = int(time.time())
        payload = {
            "iss": self.team_id,
            "iat": now,
            "exp": now + 60 * 60 * 24 * 180,
        }
        headers = {"alg": "ES256", "kid": self.key_id}
        return jwt.encode(payload, private_key, algorithm="ES256", headers=headers)

    async def search_songs(self, query: str, limit: int = 5) -> list[AppleMusicTrack]:
        token = self._build_developer_token()
        encoded_query = quote_plus(query)
        url = (
            f"https://api.music.apple.com/v1/catalog/{self.storefront}/search"
            f"?types=songs&limit={limit}&term={encoded_query}"
        )
        headers = {"Authorization": f"Bearer {token}"}
        if self.music_user_token:
            headers["Music-User-Token"] = self.music_user_token

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        payload = response.json()
        songs = payload.get("results", {}).get("songs", {}).get("data", [])
        output: list[AppleMusicTrack] = []
        for item in songs:
            attrs = item.get("attributes", {})
            previews = attrs.get("previews", [])
            preview_url = previews[0].get("url") if previews else None
            output.append(
                AppleMusicTrack(
                    id=item.get("id", ""),
                    name=attrs.get("name", ""),
                    artist=attrs.get("artistName", ""),
                    preview_url=preview_url,
                    apple_music_url=attrs.get("url"),
                )
            )
        return output
