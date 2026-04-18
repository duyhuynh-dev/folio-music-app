"""FastAPI wrapper for Folio pipeline."""

from __future__ import annotations

import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

from services.apple_music import AppleMusicClient
from pipeline.fetch import fetch_candidates
from pipeline.rank import rank_and_explain
from pipeline.scene import extract_scene
from pipeline.translate import translate_to_music_params

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


@app.get("/api/token")
def developer_token() -> dict[str, str]:
    try:
        client = AppleMusicClient()
        token = client._build_developer_token()
        return {"token": token}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/suggest-music")
async def suggest_music(
    photo: UploadFile = File(...),
    music_user_token: str = Form(default=""),
    variation_seed: int = Form(default=0),
) -> dict[str, object]:
    try:
        image_bytes = await photo.read()
        scene = extract_scene(image_bytes)
        params = translate_to_music_params(scene)
        candidates = await fetch_candidates(params, music_user_token=music_user_token or None)
        ranked = rank_and_explain(scene, candidates, variation_seed=variation_seed)
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
