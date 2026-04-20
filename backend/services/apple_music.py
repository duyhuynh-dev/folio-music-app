"""iTunes Search API client (free, no auth required).

Uses the same Apple Music catalog but via the public iTunes endpoint.
Returns 30s preview URLs that work for all users without a subscription.
"""

from __future__ import annotations

from urllib.parse import quote_plus

import httpx
from pydantic import BaseModel


class AppleMusicTrack(BaseModel):
    id: str
    name: str
    artist: str
    preview_url: str | None = None
    apple_music_url: str | None = None


class AppleMusicClient:
    BASE_URL = "https://itunes.apple.com/search"

    def __init__(
        self,
        country: str = "us",
        music_user_token: str | None = None,
    ) -> None:
        self.country = country
        self.music_user_token = music_user_token  # kept for interface compat

    def _build_developer_token(self) -> str:
        return ""

    async def search_songs(self, query: str, limit: int = 5) -> list[AppleMusicTrack]:
        encoded_query = quote_plus(query)
        url = (
            f"{self.BASE_URL}?term={encoded_query}"
            f"&media=music&entity=song&limit={limit}&country={self.country}"
        )

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        payload = response.json()
        results = payload.get("results", [])
        output: list[AppleMusicTrack] = []
        for item in results:
            output.append(
                AppleMusicTrack(
                    id=str(item.get("trackId", "")),
                    name=item.get("trackName", ""),
                    artist=item.get("artistName", ""),
                    preview_url=item.get("previewUrl"),
                    apple_music_url=item.get("trackViewUrl"),
                )
            )
        return output
