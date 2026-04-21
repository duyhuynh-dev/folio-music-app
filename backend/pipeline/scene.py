"""Stage 1 — Scene extraction via Gemini Vision."""

from __future__ import annotations

import json
import os
from io import BytesIO

from google import genai
from google.genai import types
from PIL import Image, UnidentifiedImageError
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


def _fallback_scene(image_bytes: bytes) -> Scene:
    # Conservative local fallback so uploads still work without Gemini.
    defaults = {
        "time_of_day": "midday",
        "weather": "clear",
        "energy": "moderate",
        "mood": ["contemplative"],
        "palette": "neutral",
        "cinematic_feel": 6,
    }

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            sample = image.convert("RGB").resize((64, 64))
            pixels = list(sample.getdata())
            total = len(pixels) or 1
            avg_r = sum(p[0] for p in pixels) / total
            avg_g = sum(p[1] for p in pixels) / total
            avg_b = sum(p[2] for p in pixels) / total
            brightness = (avg_r + avg_g + avg_b) / 3.0

            if brightness < 70:
                defaults["time_of_day"] = "night"
                defaults["weather"] = "overcast"
                defaults["energy"] = "quiet"
                defaults["mood"] = ["melancholic", "contemplative"]
                defaults["cinematic_feel"] = 8
            elif brightness < 135:
                defaults["time_of_day"] = "golden hour"
                defaults["weather"] = "clear"
                defaults["energy"] = "moderate"
                defaults["mood"] = ["calm", "contemplative"]
                defaults["cinematic_feel"] = 7
            else:
                defaults["time_of_day"] = "midday"
                defaults["weather"] = "clear"
                defaults["energy"] = "lively"
                defaults["mood"] = ["joyful", "uplifting"]
                defaults["cinematic_feel"] = 5

            color_spread = max(avg_r, avg_g, avg_b) - min(avg_r, avg_g, avg_b)
            if color_spread < 18:
                defaults["palette"] = "neutral"
            elif avg_r > avg_b + 8:
                defaults["palette"] = "warm"
            elif avg_b > avg_r + 8:
                defaults["palette"] = "cool"
            else:
                defaults["palette"] = "muted"
    except (UnidentifiedImageError, OSError, ValueError):
        pass

    return Scene(
        setting="travel landscape",
        time_of_day=defaults["time_of_day"],
        weather=defaults["weather"],
        energy=defaults["energy"],
        mood=defaults["mood"],
        palette=defaults["palette"],
        human_presence="none",
        movement="static",
        cinematic_feel=defaults["cinematic_feel"],
        season_feel="unclear",
    )


def extract_scene(image_bytes: bytes) -> Scene:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_scene(image_bytes)

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_text(text=SCENE_PROMPT),
                        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=700,
            ),
        )

        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        parsed = json.loads(raw)
        return Scene.model_validate(parsed)
    except Exception:
        return _fallback_scene(image_bytes)
