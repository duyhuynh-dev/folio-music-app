"""Stage 1 — Scene extraction via Gemini Vision."""

from __future__ import annotations

import base64
import json
import os

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class Scene(BaseModel):
    setting: str
    time_of_day: str
    weather: str
    energy: str
    mood: list[str] = Field(default_factory=list)
    palette: str
    human_presence: str
    movement: str
    cinematic_feel: int = Field(ge=0, le=10)
    season_feel: str


SCENE_PROMPT = """
Analyse this travel photo and return ONLY valid JSON:
{
  "setting": "coastal cliff / mountain / city street / etc",
  "time_of_day": "golden hour / midday / night / etc",
  "weather": "clear / misty / overcast / stormy",
  "energy": "still | quiet | moderate | lively | chaotic",
  "mood": ["contemplative", "joyful", "melancholic"],
  "palette": "warm | cool | neutral | vivid | muted",
  "human_presence": "none | solitary | small group | crowd",
  "movement": "static | slow | dynamic",
  "cinematic_feel": 0-10,
  "season_feel": "summer | autumn | winter | spring | unclear"
}
Do not include any markdown fences or extra keys.
""".strip()


def extract_scene(image_bytes: bytes) -> Scene:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in environment.")

    client = genai.Client(api_key=api_key)
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Content(
                parts=[
                    types.Part.from_text(text=SCENE_PROMPT),
                    types.Part.from_bytes(data=base64.b64decode(b64), mime_type="image/jpeg"),
                ]
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=700,
        ),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    parsed = json.loads(raw)
    return Scene.model_validate(parsed)
