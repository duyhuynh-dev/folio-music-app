"""Feedback loop — builds few-shot examples from accepted taste signals.

Pulls the user's accepted scene→track pairs from Supabase and formats
them as examples for the translate (Stage 2) and rank (Stage 4) prompts.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from supabase import create_client

_LOCAL_TASTE_SIGNALS: list[dict] = []


def _supabase():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)


def record_taste_signal(
    user_id: str,
    track_id: str,
    track_name: str,
    track_artist: str,
    action: str,
    scene_json: dict,
    moment_id: str | None = None,
) -> None:
    payload = {
        "user_id": user_id,
        "moment_id": moment_id or None,
        "track_id": track_id,
        "track_name": track_name,
        "track_artist": track_artist,
        "action": action,
        "scene_json": scene_json,
    }

    sb = _supabase()
    if sb:
        sb.table("taste_signals").insert(payload).execute()
        return

    _LOCAL_TASTE_SIGNALS.append({
        **payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def get_taste_signals(user_id: str, limit: int = 200, action: str | None = None) -> list[dict]:
    sb = _supabase()
    if sb:
        query = (
            sb.table("taste_signals")
            .select("scene_json, track_name, track_artist, action, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if action:
            query = query.eq("action", action)
        result = query.execute()
        return result.data or []

    filtered: list[dict] = []
    for signal in reversed(_LOCAL_TASTE_SIGNALS):
        if signal.get("user_id") != user_id:
            continue
        if action and signal.get("action") != action:
            continue
        filtered.append(signal)
        if len(filtered) >= limit:
            break
    return filtered


def get_few_shot_examples(user_id: str, limit: int = 5) -> list[dict]:
    signals = get_taste_signals(user_id=user_id, limit=limit, action="accept")

    examples = []
    for s in signals:
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
