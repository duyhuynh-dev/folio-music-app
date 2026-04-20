"""Stage 2 — Scene JSON → music search parameters."""

from __future__ import annotations

import json
import os

from anthropic import Anthropic
from pydantic import BaseModel, Field

from .scene import Scene


class MusicParams(BaseModel):
    search_queries: list[str] = Field(default_factory=list, min_length=1)
    lastfm_tags: list[str] = Field(default_factory=list)
    seed_artists: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    tempo: str


def _extract_text_content(response: object) -> str:
    content = getattr(response, "content", []) or []
    text_parts: list[str] = []
    for block in content:
        if getattr(block, "type", "") == "text":
            text_parts.append(getattr(block, "text", ""))
    return "\n".join(text_parts).strip()


def translate_to_music_params(scene: Scene, user_taste_context: str = "") -> MusicParams:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY in environment.")

    client = Anthropic(api_key=api_key)
    scene_json = scene.model_dump_json(indent=2)

    taste_block = f"\n\n{user_taste_context}" if user_taste_context else ""

    prompt = f"""
You are translating a travel-scene descriptor into music-discovery parameters.
Return ONLY valid JSON with this schema:
{{
  "search_queries": ["..."],
  "lastfm_tags": ["..."],
  "seed_artists": ["..."],
  "avoid": ["..."],
  "tempo": "slow | medium | fast"
}}

Constraints:
- 2 to 4 search queries, each 3-7 words.
- lastfm_tags should be practical mood tags.
- avoid should include opposite energies/moods.
- No markdown fences.

Scene:
{scene_json}{taste_block}
""".strip()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=700,
        temperature=0.4,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text_content(response)
    parsed = json.loads(raw)
    return MusicParams.model_validate(parsed)
