"""CLI runner for the Folio pipeline (Phase 1).

Usage:
    python run.py path/to/photo.jpg
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from pipeline.fetch import fetch_candidates
from pipeline.rank import rank_and_explain
from pipeline.scene import extract_scene
from pipeline.translate import translate_to_music_params

load_dotenv()


async def run(photo_path: Path) -> None:
    image_bytes = photo_path.read_bytes()

    scene = extract_scene(image_bytes)
    print("== Scene ==")
    print(scene.model_dump_json(indent=2))

    params = translate_to_music_params(scene)
    print("\n== Music params ==")
    print(params.model_dump_json(indent=2))

    candidates = await fetch_candidates(params)
    print(f"\n== {len(candidates)} candidates ==")

    final = rank_and_explain(scene, candidates)
    print("\n== Final 4 ==")
    print(json.dumps([t.model_dump() for t in final], indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run.py <photo_path>")
        sys.exit(1)
    asyncio.run(run(Path(sys.argv[1])))
