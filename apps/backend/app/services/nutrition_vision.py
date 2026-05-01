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


def _normalize_image_mime(mime: str) -> str:
    if mime in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        return mime
    return "image/jpeg"


def _prompts(user_lang: str, diet_notes: str | None) -> tuple[str, str]:
    lang_line = "Russian" if user_lang != "en" else "English"
    diet = (diet_notes or "").strip()[:500]
    system = (
        "You estimate food calories from a photo. Reply ONLY valid JSON, no markdown.\n"
        "Schema: {\"total_kcal\": int, \"confidence\": float 0-1, \"meal_type_guess\": "
        "\"breakfast|lunch|dinner|snack|unknown\", \"description\": string, "
        "\"items\": [{\"name\": string, \"estimated_kcal\": int, \"grams_guess\": int}]}\n"
        "Be conservative if unsure; lower confidence. Respect allergies/diet notes if provided."
    )
    user_text = (
        f"Language for description: {lang_line}. Diet notes: {diet or 'none'}. "
        "Analyze the attached meal photo."
    )
    return system, user_text


def _parse_vision_response(content: str) -> dict[str, Any]:
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


async def _analyze_food_image_anthropic(
    image_bytes: bytes, mime: str, user_lang: str, diet_notes: str | None
) -> dict[str, Any]:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_NOT_CONFIGURED")

    mime = _normalize_image_mime(mime)
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    system, user_text = _prompts(user_lang, diet_notes)
    timeout = max(float(settings.anthropic_timeout_sec), 60.0)

    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 700,
        "system": system,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": mime, "data": b64},
                    },
                    {"type": "text", "text": user_text},
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )
        r.raise_for_status()
        body = r.json()

    text_parts: list[str] = []
    for block in body.get("content", []) or []:
        if block.get("type") == "text":
            t = (block.get("text") or "").strip()
            if t:
                text_parts.append(t)
    content = "\n".join(text_parts)
    return _parse_vision_response(content)


async def _analyze_food_image_openai(
    image_bytes: bytes, mime: str, user_lang: str, diet_notes: str | None
) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_NOT_CONFIGURED")

    mime = _normalize_image_mime(mime)
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    system, user_text = _prompts(user_lang, diet_notes)

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
    return _parse_vision_response(content)


async def analyze_food_image(image_bytes: bytes, mime: str, user_lang: str, diet_notes: str | None) -> dict[str, Any]:
    """Prefer Anthropic when ANTHROPIC_API_KEY is set; otherwise OpenAI vision."""
    if settings.anthropic_api_key:
        return await _analyze_food_image_anthropic(image_bytes, mime, user_lang, diet_notes)
    if settings.openai_api_key:
        return await _analyze_food_image_openai(image_bytes, mime, user_lang, diet_notes)
    raise RuntimeError("AI_VISION_NOT_CONFIGURED")
