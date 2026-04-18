"""Last.fm Tag API client."""

from __future__ import annotations

import os

import httpx
from pydantic import BaseModel


class LastfmTrack(BaseModel):
    name: str
    artist: str


class LastfmClient:
    BASE_URL = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self) -> None:
        self.api_key = os.getenv("LASTFM_API_KEY")

    async def get_top_tracks_by_tag(self, tag: str, limit: int = 5) -> list[LastfmTrack]:
        if not self.api_key:
            raise RuntimeError("Missing LASTFM_API_KEY in environment.")

        params = {
            "method": "tag.gettoptracks",
            "tag": tag,
            "api_key": self.api_key,
            "format": "json",
            "limit": limit,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()

        payload = response.json()
        tracks = payload.get("tracks", {}).get("track", [])
        output: list[LastfmTrack] = []
        for item in tracks:
            artist = item.get("artist", {})
            output.append(
                LastfmTrack(
                    name=item.get("name", ""),
                    artist=artist.get("name", "") if isinstance(artist, dict) else "",
                )
            )
        return output
