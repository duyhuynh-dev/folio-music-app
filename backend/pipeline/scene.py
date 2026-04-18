"""Stage 1 — Scene extraction via Claude Vision."""

from __future__ import annotations

import base64
import json
import os

from anthropic import Anthropic
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


def _extract_text_content(response: object) -> str:
    content = getattr(response, "content", []) or []
    text_parts: list[str] = []
    for block in content:
        if getattr(block, "type", "") == "text":
            text_parts.append(getattr(block, "text", ""))
    return "\n".join(text_parts).strip()


def extract_scene(image_bytes: bytes) -> Scene:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY in environment.")

    client = Anthropic(api_key=api_key)
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
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

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=700,
        temperature=0.2,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image,
                        },
                    },
                ],
            }
        ],
    )

    raw = _extract_text_content(response)
    parsed = json.loads(raw)
    return Scene.model_validate(parsed)
