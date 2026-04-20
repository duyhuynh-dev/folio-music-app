"""Stage 2 — Scene JSON → music search parameters."""

from __future__ import annotations

import json
import os

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from .scene import Scene


class MusicParams(BaseModel):
    search_queries: list[str] = Field(default_factory=list, min_length=1)
    lastfm_tags: list[str] = Field(default_factory=list)
    seed_artists: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    tempo: str


def translate_to_music_params(scene: Scene, user_taste_context: str = "") -> MusicParams:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in environment.")

    client = genai.Client(api_key=api_key)
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

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=700,
        ),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    parsed = json.loads(raw)
    return MusicParams.model_validate(parsed)
