"""FastAPI wrapper for Folio pipeline (Phase 2.1 ready)."""

from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services.apple_music import AppleMusicClient
from pipeline.fetch import fetch_candidates
from pipeline.rank import rank_and_explain
from pipeline.scene import extract_scene
from pipeline.translate import translate_to_music_params

app = FastAPI(title="Folio API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


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
