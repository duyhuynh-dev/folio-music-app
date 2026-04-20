"""Feedback loop — builds few-shot examples from accepted taste signals.

Pulls the user's accepted scene→track pairs from Supabase and formats
them as examples for the translate (Stage 2) and rank (Stage 4) prompts.
"""

from __future__ import annotations

import json
import os

from supabase import create_client


def _supabase():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)


def get_few_shot_examples(user_id: str, limit: int = 5) -> list[dict]:
    sb = _supabase()
    if not sb:
        return []

    signals = (
        sb.table("taste_signals")
        .select("scene_json, track_name, track_artist, action")
        .eq("user_id", user_id)
        .eq("action", "accept")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    examples = []
    for s in signals.data or []:
        scene = s.get("scene_json")
        if not scene or not s.get("track_name"):
            continue
        examples.append({
            "scene": scene if isinstance(scene, dict) else {},
            "chosen_track": f"{s['track_name']} — {s['track_artist']}",
        })

    return examples


def format_examples_for_translate(examples: list[dict]) -> str:
    if not examples:
        return ""

    lines = [
        "Here are examples of scenes this user previously matched with music they loved:"
    ]
    for i, ex in enumerate(examples, 1):
        scene_summary = json.dumps(ex["scene"], indent=None)
        lines.append(f"  {i}. Scene: {scene_summary}")
        lines.append(f"     Chosen: {ex['chosen_track']}")

    lines.append(
        "Use these as guidance for this user's taste — lean toward similar "
        "moods and artists when the scene feels similar."
    )
    return "\n".join(lines)


def format_examples_for_rank(examples: list[dict]) -> str:
    if not examples:
        return ""

    lines = [
        "This user has previously chosen these tracks for similar scenes:"
    ]
    for ex in examples:
        lines.append(f"  - {ex['chosen_track']}")

    lines.append(
        "Prefer candidates that align with this taste profile when ranking."
    )
    return "\n".join(lines)
