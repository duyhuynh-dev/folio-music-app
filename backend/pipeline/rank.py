"""Stage 4 — Re-rank candidates and generate per-track reasons."""

from __future__ import annotations

import json
import os

from anthropic import Anthropic
from pydantic import BaseModel

from .fetch import TrackCandidate
from .scene import Scene


class RankedTrack(BaseModel):
    id: str
    name: str
    artist: str
    preview_url: str | None = None
    apple_music_url: str | None = None
    reason: str


def _extract_text_content(response: object) -> str:
    content = getattr(response, "content", []) or []
    text_parts: list[str] = []
    for block in content:
        if getattr(block, "type", "") == "text":
            text_parts.append(getattr(block, "text", ""))
    return "\n".join(text_parts).strip()


def rank_and_explain(
    scene: Scene,
    candidates: list[TrackCandidate],
    variation_seed: int = 0,
    user_taste_context: str = "",
) -> list[RankedTrack]:
    if not candidates:
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Fallback for local development if key is missing.
        return [
            RankedTrack(
                id=t.id,
                name=t.name,
                artist=t.artist,
                preview_url=t.preview_url,
                apple_music_url=t.apple_music_url,
                reason=(
                    "Strong mood alignment with the photo's tone, chosen in "
                    "fallback mode without AI ranking."
                ),
            )
            for t in candidates[:4]
        ]

    client = Anthropic(api_key=api_key)
    scene_json = scene.model_dump_json(indent=2)
    candidates_json = json.dumps([c.model_dump() for c in candidates], indent=2)

    prompt = f"""
You are ranking song candidates for a travel photo.
Return ONLY valid JSON array of exactly 4 items.
Each item must use this schema:
{{
  "id": "candidate id",
  "name": "track name",
  "artist": "artist",
  "reason": "one short line tied to visible scene details"
}}

Rules:
- Choose from provided candidates only.
- Keep reasons under 16 words.
- variation_seed must influence diversity so reruns can feel different.
- No markdown fences.

variation_seed: {variation_seed}
scene: {scene_json}
candidates: {candidates_json}
{user_taste_context}
""".strip()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        temperature=0.6,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text_content(response)
    ranked_payload = json.loads(raw)

    candidate_by_id = {c.id: c for c in candidates}
    output: list[RankedTrack] = []
    for item in ranked_payload:
        original = candidate_by_id.get(item["id"])
        if not original:
            continue
        output.append(
            RankedTrack(
                id=original.id,
                name=original.name,
                artist=original.artist,
                preview_url=original.preview_url,
                apple_music_url=original.apple_music_url,
                reason=item["reason"],
            )
        )

    return output[:4]
