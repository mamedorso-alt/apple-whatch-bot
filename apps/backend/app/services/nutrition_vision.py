from __future__ import annotations

import base64
import json
import re
from typing import Any

import httpx

from app.core.config import get_settings

settings = get_settings()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


async def analyze_food_image(image_bytes: bytes, mime: str, user_lang: str, diet_notes: str | None) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_NOT_CONFIGURED")

    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        mime = "image/jpeg"
    lang_line = "Russian" if user_lang != "en" else "English"
    diet = (diet_notes or "").strip()[:500]
    system = (
        "You estimate food calories from a photo. Reply ONLY valid JSON, no markdown.\n"
        "Schema: {\"total_kcal\": int, \"confidence\": float 0-1, \"meal_type_guess\": "
        "\"breakfast|lunch|dinner|snack|unknown\", \"description\": string, "
        "\"items\": [{\"name\": string, \"estimated_kcal\": int, \"grams_guess\": int}]}\n"
        "Be conservative if unsure; lower confidence. Respect allergies/diet notes if provided."
    )
    user_text = f"Language for description: {lang_line}. Diet notes: {diet or 'none'}."

    payload = {
        "model": settings.openai_vision_model,
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "low"},
                    },
                ],
            },
        ],
    }

    async with httpx.AsyncClient(timeout=settings.openai_timeout_sec) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        body = r.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    parsed = _extract_json_object(content)
    if not parsed:
        return {
            "total_kcal": None,
            "confidence": 0.2,
            "meal_type_guess": "unknown",
            "description": content[:400] if content else "parse_error",
            "items": [],
            "raw_text": content[:800],
        }
    return parsed
