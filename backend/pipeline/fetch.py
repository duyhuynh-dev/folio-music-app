"""Stage 3 — Track retrieval from Apple Music + Last.fm."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from services.apple_music import AppleMusicClient
from services.lastfm import LastfmClient

from .translate import MusicParams


class TrackCandidate(BaseModel):
    id: str
    name: str
    artist: str
    preview_url: str | None = None
    apple_music_url: str | None = None
    source: str  # "apple_music" | "lastfm"


def _track_key(name: str, artist: str) -> str:
    return f"{name.strip().lower()}::{artist.strip().lower()}"


async def fetch_candidates(
    params: MusicParams,
    music_user_token: str | None = None,
) -> list[TrackCandidate]:
    apple = AppleMusicClient(music_user_token=music_user_token)
    lastfm = LastfmClient()

    apple_tasks = [apple.search_songs(query=q, limit=4) for q in params.search_queries]
    lastfm_tasks = [lastfm.get_top_tracks_by_tag(tag=t, limit=4) for t in params.lastfm_tags]

    apple_results, lastfm_results = await asyncio.gather(
        asyncio.gather(*apple_tasks) if apple_tasks else asyncio.sleep(0, result=[]),
        asyncio.gather(*lastfm_tasks) if lastfm_tasks else asyncio.sleep(0, result=[]),
    )

    deduped: dict[str, TrackCandidate] = {}

    for tracks in apple_results:
        for t in tracks:
            key = _track_key(t.name, t.artist)
            if key not in deduped:
                deduped[key] = TrackCandidate(
                    id=f"am_{t.id}",
                    name=t.name,
                    artist=t.artist,
                    preview_url=t.preview_url,
                    apple_music_url=t.apple_music_url,
                    source="apple_music",
                )

    cross_ref_queries: list[str] = []
    for tracks in lastfm_results:
        for t in tracks:
            cross_ref_queries.append(f"{t.name} {t.artist}".strip())

    if cross_ref_queries:
        cross_ref_hits = await asyncio.gather(
            *(apple.search_songs(query=q, limit=1) for q in cross_ref_queries)
        )
        for hits in cross_ref_hits:
            if not hits:
                continue
            t = hits[0]
            key = _track_key(t.name, t.artist)
            if key not in deduped:
                deduped[key] = TrackCandidate(
                    id=f"am_{t.id}",
                    name=t.name,
                    artist=t.artist,
                    preview_url=t.preview_url,
                    apple_music_url=t.apple_music_url,
                    source="lastfm",
                )

    return list(deduped.values())[:10]
