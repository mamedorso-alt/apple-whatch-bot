from app.services.reels_support import parse_reels_telegram_user_ids, reels_allowlisted_ids
from app.services.telegram import chunk_telegram_text


def test_parse_reels_telegram_user_ids():
    assert parse_reels_telegram_user_ids("") == []
    assert parse_reels_telegram_user_ids("123, 456, abc, 789") == [123, 456, 789]


def test_chunk_telegram_text_splits_long():
    body = "a\n\n" + ("x" * 5000)
    parts = chunk_telegram_text(body, limit=2000)
    assert len(parts) >= 2
    assert all(len(p) <= 2000 for p in parts)


def test_reels_allowlisted_ids_respects_settings(monkeypatch):
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("REELS_AGENT_TELEGRAM_USER_IDS", "42, 43")
    get_settings.cache_clear()
    assert reels_allowlisted_ids() == {42, 43}
    get_settings.cache_clear()
