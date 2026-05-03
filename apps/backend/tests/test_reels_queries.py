"""Unit tests for reels search query shaping (no network)."""

from app.services import reels_agent as ra


def test_search_queries_ru_burnout_german_psychiatrist():
    hint = (
        "Я знаю что этот термин был придуман немецким Психиатром, а до него такого понятия не существовало. "
        "Каждый эксперт кричит про выгорание."
    )
    qs = ra._search_queries_from_user_hint(hint, "ru")
    flat = " ".join(qs).lower()
    assert "выгоран" in flat or "freudenberger" in flat
    assert len(qs) >= 4
    assert all(len(q) < 250 for q in qs)


def test_first_sentence_chunk_truncates_long_paragraph():
    t = "А это очень длинное предложение без точки с запятой " * 20
    c = ra._first_sentence_chunk(t, max_len=80)
    assert len(c) <= 80


def test_search_queries_en_burnout():
    qs = ra._search_queries_from_user_hint("Burnout is overused by coaches to sell courses", "en")
    assert len(qs) >= 3
    assert any("burnout" in q.lower() for q in qs)
