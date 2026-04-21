"""FastAPI wrapper for Folio pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from supabase import create_client

from services.feedback_loop import (
    format_examples_for_rank,
    format_examples_for_translate,
    get_few_shot_examples,
    get_taste_signals,
    record_taste_signal,
)
from services.video_export import generate_trip_video
from pipeline.fetch import fetch_candidates
from pipeline.rank import rank_and_explain
from pipeline.scene import extract_scene
from pipeline.translate import translate_to_music_params

# Load backend/.env when running via uvicorn (which does not call run.py).
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

app = FastAPI(title="Folio API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _supabase():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    return create_client(url, key)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/suggest-music")
async def suggest_music(
    photo: UploadFile = File(...),
    music_user_token: str = Form(default=""),
    variation_seed: int = Form(default=0),
    user_id: str = Form(default=""),
) -> dict[str, object]:
    try:
        image_bytes = await photo.read()
        scene = extract_scene(image_bytes)

        translate_ctx = ""
        rank_ctx = ""
        if user_id:
            examples = get_few_shot_examples(user_id, limit=5)
            translate_ctx = format_examples_for_translate(examples)
            rank_ctx = format_examples_for_rank(examples)

        params = translate_to_music_params(scene, user_taste_context=translate_ctx)
        candidates = await fetch_candidates(params, music_user_token=music_user_token or None)
        ranked = rank_and_explain(scene, candidates, variation_seed=variation_seed, user_taste_context=rank_ctx)
        return {"scene": scene.model_dump(), "suggestions": [t.model_dump() for t in ranked]}
    except Exception as exc:  # pragma: no cover - keeps API return shape stable
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/trips/{trip_id}")
def get_trip(trip_id: str) -> dict[str, object]:
    sb = _supabase()
    trip = sb.table("trips").select("*").eq("id", trip_id).maybe_single().execute()
    if not trip.data:
        raise HTTPException(status_code=404, detail="Trip not found")

    moments = (
        sb.table("moments")
        .select("*")
        .eq("trip_id", trip_id)
        .order("taken_at")
        .execute()
    )

    return {"trip": trip.data, "moments": moments.data or []}


@app.post("/api/trips")
def create_trip(
    title: str = Form(default="Untitled Trip"),
    user_id: str = Form(...),
) -> dict[str, object]:
    sb = _supabase()
    result = sb.table("trips").insert({"title": title, "user_id": user_id}).execute()
    return {"trip": result.data[0] if result.data else {}}


@app.post("/api/trips/{trip_id}/moments")
def add_moment(
    trip_id: str,
    user_id: str = Form(...),
    photo_url: str = Form(...),
    chosen_track_id: str = Form(default=""),
    chosen_track_name: str = Form(default=""),
    chosen_track_artist: str = Form(default=""),
    chosen_track_reason: str = Form(default=""),
    chosen_track_apple_url: str = Form(default=""),
    chosen_track_preview_url: str = Form(default=""),
    latitude: float = Form(default=0.0),
    longitude: float = Form(default=0.0),
    scene_json: str = Form(default="{}"),
) -> dict[str, object]:
    import json

    sb = _supabase()
    result = sb.table("moments").insert({
        "trip_id": trip_id,
        "user_id": user_id,
        "photo_url": photo_url,
        "scene_json": json.loads(scene_json),
        "chosen_track_id": chosen_track_id or None,
        "chosen_track_name": chosen_track_name or None,
        "chosen_track_artist": chosen_track_artist or None,
        "chosen_track_reason": chosen_track_reason or None,
        "chosen_track_apple_url": chosen_track_apple_url or None,
        "chosen_track_preview_url": chosen_track_preview_url or None,
        "latitude": latitude or None,
        "longitude": longitude or None,
    }).execute()
    return {"moment": result.data[0] if result.data else {}}


@app.post("/api/trips/{trip_id}/export-video")
async def export_video(trip_id: str) -> FileResponse:
    sb = _supabase()
    moments = (
        sb.table("moments")
        .select("photo_url, chosen_track_preview_url")
        .eq("trip_id", trip_id)
        .order("taken_at")
        .execute()
    )
    if not moments.data:
        raise HTTPException(status_code=404, detail="No moments found for this trip")

    output_path = await generate_trip_video(moments.data)
    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"folio_trip_{trip_id[:8]}.mp4",
    )


@app.get("/api/rewind/{user_id}/{year}")
def annual_rewind(user_id: str, year: int) -> dict[str, object]:
    sb = _supabase()
    trips = (
        sb.table("trips")
        .select("*")
        .eq("user_id", user_id)
        .gte("created_at", f"{year}-01-01")
        .lt("created_at", f"{year + 1}-01-01")
        .order("created_at")
        .execute()
    )
    if not trips.data:
        raise HTTPException(status_code=404, detail="No trips found for this year")

    trip_ids = [t["id"] for t in trips.data]
    all_moments = (
        sb.table("moments")
        .select("*")
        .in_("trip_id", trip_ids)
        .order("taken_at")
        .execute()
    )

    return {
        "year": year,
        "total_trips": len(trips.data),
        "total_moments": len(all_moments.data or []),
        "trips": trips.data,
        "moments": all_moments.data or [],
    }


@app.post("/api/taste")
def log_taste_signal(
    user_id: str = Form(...),
    track_id: str = Form(...),
    track_name: str = Form(...),
    track_artist: str = Form(...),
    action: str = Form(...),
    moment_id: str = Form(default=""),
    scene_json: str = Form(default="{}"),
) -> dict[str, str]:
    import json

    if action not in ("accept", "reject", "try_different"):
        raise HTTPException(status_code=400, detail="action must be accept, reject, or try_different")

    try:
        parsed_scene = json.loads(scene_json)
    except json.JSONDecodeError:
        parsed_scene = {}

    record_taste_signal(
        user_id=user_id,
        moment_id=moment_id or None,
        track_id=track_id,
        track_name=track_name,
        track_artist=track_artist,
        action=action,
        scene_json=parsed_scene if isinstance(parsed_scene, dict) else {},
    )

    return {"status": "recorded"}


@app.get("/api/taste/{user_id}/preferences")
def get_taste_preferences(user_id: str) -> dict[str, object]:
    signals = get_taste_signals(user_id=user_id, limit=200)

    artist_scores: dict[str, int] = {}
    for s in signals:
        artist = s.get("track_artist", "")
        if not artist:
            continue
        delta = 1 if s["action"] == "accept" else -1
        artist_scores[artist] = artist_scores.get(artist, 0) + delta

    preferred = sorted(
        [(a, sc) for a, sc in artist_scores.items() if sc > 0],
        key=lambda x: x[1],
        reverse=True,
    )
    avoided = sorted(
        [(a, sc) for a, sc in artist_scores.items() if sc < 0],
        key=lambda x: x[1],
    )

    return {
        "preferred_artists": [a for a, _ in preferred[:20]],
        "avoided_artists": [a for a, _ in avoided[:20]],
    }


@app.get("/api/taste/{user_id}/personalisation")
async def get_personalisation_context(
    user_id: str,
    lastfm_username: str = "",
) -> dict[str, object]:
    from services.lastfm import LastfmClient

    signals = get_taste_signals(user_id=user_id, limit=200)

    artist_scores: dict[str, int] = {}
    for s in signals:
        artist = s.get("track_artist", "")
        if not artist:
            continue
        delta = 1 if s["action"] == "accept" else -1
        artist_scores[artist] = artist_scores.get(artist, 0) + delta

    preferred = [a for a, sc in artist_scores.items() if sc > 0]
    avoided = [a for a, sc in artist_scores.items() if sc < 0]

    lastfm_top: list[str] = []
    if lastfm_username:
        client = LastfmClient()
        lastfm_top = await client.get_user_top_artists(lastfm_username, limit=15)

    combined_preferred = list(dict.fromkeys(preferred + lastfm_top))[:25]

    return {
        "preferred_artists": combined_preferred,
        "avoided_artists": avoided[:20],
        "lastfm_top_artists": lastfm_top,
        "taste_signal_count": len(signals),
    }
