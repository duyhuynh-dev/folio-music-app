"""Stage 4 — Re-rank candidates and generate per-track reasons."""

from __future__ import annotations

import hashlib
import json
import os
import re

from google import genai
from google.genai import types
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


TOKEN_RE = re.compile(r"[a-z0-9]+")
TITLE_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "for",
    "in",
    "on",
    "at",
    "with",
    "feat",
    "featuring",
    "pt",
    "part",
    "vol",
}
LOW_SIGNAL_TERMS = {
    "karaoke",
    "instrumental",
    "sound effect",
    "white noise",
    "binaural",
    "study",
    "workout",
    "nightcore",
    "slowed",
    "reverb",
    "sped up",
}
SYNONYMS: dict[str, set[str]] = {
    "night": {"midnight", "moonlight", "afterhours", "dark"},
    "city": {"urban", "downtown", "skyline", "streets"},
    "bridge": {"crossing", "river"},
    "quiet": {"calm", "still", "soft", "gentle"},
    "lively": {"energetic", "upbeat", "dance", "party"},
    "melancholic": {"melancholy", "wistful", "reflective"},
    "joyful": {"happy", "uplifting", "bright"},
    "warm": {"sunset", "golden"},
    "cool": {"blue", "neon"},
    "clear": {"crisp", "clean"},
    "overcast": {"mist", "fog", "rain", "drizzle"},
}


def _tokens(value: str) -> set[str]:
    return {t for t in TOKEN_RE.findall(value.lower()) if len(t) > 1}


def _track_signature(name: str) -> str:
    tokens = [t for t in TOKEN_RE.findall(name.lower()) if t not in TITLE_STOPWORDS]
    if not tokens:
        return name.strip().lower()
    return " ".join(tokens[:3])


def _stable_jitter(track_id: str, variation_seed: int) -> float:
    digest = hashlib.sha256(f"{track_id}:{variation_seed}".encode("utf-8")).digest()
    unit = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
    return (unit - 0.5) * 0.2


def _scene_positive_terms(scene: Scene) -> set[str]:
    positive = _tokens(
        " ".join(
            [
                scene.setting,
                scene.time_of_day,
                scene.weather,
                scene.energy,
                scene.palette,
                scene.season_feel,
                " ".join(scene.mood),
            ]
        )
    )
    expanded = set(positive)
    for term in list(positive):
        expanded.update(SYNONYMS.get(term, set()))
    return expanded


def _scene_negative_terms(scene: Scene) -> set[str]:
    negative: set[str] = set()
    weather = scene.weather.lower()
    time_of_day = scene.time_of_day.lower()
    energy = scene.energy.lower()

    if weather == "clear":
        negative.update({"rain", "drizzle", "storm", "thunder"})
    if weather in {"stormy", "misty", "overcast"}:
        negative.update({"sunny", "beach"})

    if "night" in time_of_day:
        negative.update({"sunrise", "morning", "noon"})
    if time_of_day in {"midday", "morning"}:
        negative.update({"midnight", "afterhours"})

    if energy in {"still", "quiet"}:
        negative.update({"hardcore", "rage", "party", "club", "chaotic", "phonk"})
    if energy in {"lively", "chaotic"}:
        negative.update({"sleep", "lullaby", "ambient"})

    return negative


def _fallback_reason(scene: Scene, matched_terms: list[str]) -> str:
    if matched_terms:
        top = ", ".join(matched_terms[:2])
        return f"Matches {top} cues from your scene in fallback ranking."
    mood = scene.mood[0] if scene.mood else "travel"
    return f"Fits a {mood} {scene.time_of_day} vibe in fallback ranking."


def _fallback_rank(
    scene: Scene,
    candidates: list[TrackCandidate],
    variation_seed: int,
) -> list[RankedTrack]:
    if not candidates:
        return []

    positive_terms = _scene_positive_terms(scene)
    negative_terms = _scene_negative_terms(scene)

    selected: list[tuple[TrackCandidate, list[str]]] = []
    selected_artists: set[str] = set()
    selected_titles: set[str] = set()
    remaining = list(candidates)

    while remaining and len(selected) < 4:
        best: tuple[float, TrackCandidate, list[str]] | None = None

        for track in remaining:
            haystack = f"{track.name} {track.artist}".lower()
            track_terms = _tokens(haystack)
            matched = sorted(positive_terms.intersection(track_terms))
            mismatched = sorted(negative_terms.intersection(track_terms))

            score = 0.0
            score += len(matched) * 1.3
            score -= len(mismatched) * 2.0

            low_signal_hits = [term for term in LOW_SIGNAL_TERMS if term in haystack]
            score -= len(low_signal_hits) * 1.2

            if track.preview_url:
                score += 0.3
            if track.source == "apple_music":
                score += 0.2

            signature = _track_signature(track.name)
            artist_key = track.artist.strip().lower()
            if signature in selected_titles:
                score -= 0.9
            if artist_key in selected_artists:
                score -= 0.5

            score += _stable_jitter(track.id, variation_seed)

            if best is None or score > best[0]:
                best = (score, track, matched)

        if best is None:
            break

        _, best_track, matched_terms = best
        selected.append((best_track, matched_terms))
        selected_artists.add(best_track.artist.strip().lower())
        selected_titles.add(_track_signature(best_track.name))
        remaining = [track for track in remaining if track.id != best_track.id]

    return [
        RankedTrack(
            id=track.id,
            name=track.name,
            artist=track.artist,
            preview_url=track.preview_url,
            apple_music_url=track.apple_music_url,
            reason=_fallback_reason(scene, matched_terms),
        )
        for track, matched_terms in selected
    ]


def rank_and_explain(
    scene: Scene,
    candidates: list[TrackCandidate],
    variation_seed: int = 0,
    user_taste_context: str = "",
) -> list[RankedTrack]:
    if not candidates:
        return []

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_rank(scene, candidates, variation_seed)

    client = genai.Client(api_key=api_key)
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

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.6,
                max_output_tokens=800,
            ),
        )

        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        ranked_payload = json.loads(raw)
    except Exception:
        return _fallback_rank(scene, candidates, variation_seed)

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

    return output[:4] if output else _fallback_rank(scene, candidates, variation_seed)
