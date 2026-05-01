from __future__ import annotations

import asyncio

import pytest

import app.services.nutrition_vision as nv


def test_analyze_prefers_anthropic_when_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    class S:
        anthropic_api_key = "anthropic-key"
        openai_api_key = "openai-key"

    monkeypatch.setattr(nv, "settings", S())
    called: list[str] = []

    async def fake_anthropic(*_a, **_k):
        called.append("anthropic")
        return {"total_kcal": 100, "confidence": 0.5, "meal_type_guess": "lunch", "description": "ok", "items": []}

    async def fake_openai(*_a, **_k):
        called.append("openai")
        raise AssertionError("OpenAI should not run when Anthropic key is set")

    monkeypatch.setattr(nv, "_analyze_food_image_anthropic", fake_anthropic)
    monkeypatch.setattr(nv, "_analyze_food_image_openai", fake_openai)

    out = asyncio.run(nv.analyze_food_image(b"\xff\xd8", "image/jpeg", "ru", None))
    assert called == ["anthropic"]
    assert out["total_kcal"] == 100


def test_analyze_openai_when_only_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    class S:
        anthropic_api_key = ""
        openai_api_key = "openai-key"

    monkeypatch.setattr(nv, "settings", S())
    called: list[str] = []

    async def fake_anthropic(*_a, **_k):
        called.append("anthropic")
        raise AssertionError("Anthropic should not run")

    async def fake_openai(*_a, **_k):
        called.append("openai")
        return {"total_kcal": 200, "confidence": 0.6, "meal_type_guess": "dinner", "description": "ok", "items": []}

    monkeypatch.setattr(nv, "_analyze_food_image_anthropic", fake_anthropic)
    monkeypatch.setattr(nv, "_analyze_food_image_openai", fake_openai)

    out = asyncio.run(nv.analyze_food_image(b"x", "image/png", "en", None))
    assert called == ["openai"]
    assert out["total_kcal"] == 200


def test_analyze_raises_without_any_key(monkeypatch: pytest.MonkeyPatch) -> None:
    class S:
        anthropic_api_key = ""
        openai_api_key = ""

    monkeypatch.setattr(nv, "settings", S())
    with pytest.raises(RuntimeError, match="AI_VISION_NOT_CONFIGURED"):
        asyncio.run(nv.analyze_food_image(b"x", "image/jpeg", "ru", None))
