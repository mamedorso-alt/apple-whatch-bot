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


def test_reels_output_failed_spec_refusal_ru():
    bad = "Интересная тема, но я не буду разносить концепцию выгорания — это несправедливо. " * 15
    assert ra._reels_output_failed_spec(bad, "ru") is True


def test_reels_output_failed_spec_wellness_pivot_ru():
    bad = (
        "Сон: 0 минут. Шаги: 328. Скор: 42 из 100. Активность почти ноль. "
        "Это конкретные факты твоего тела сегодня. Что происходит? " * 8
    )
    assert ra._reels_output_failed_spec(bad, "ru") is True


def test_reels_output_failed_spec_ok_script_ru():
    ok = (
        "1) Шаг 1 — Тема: хайп вокруг слова «выгорание» в соцсетях.\n"
        "2) Шаг 2 — Спорное утверждение: все «выгорели» без критериев.\n"
        "3) Шаг 2 — Опровержение: термин появился в 1970-х; см. сниппеты.\n"
        "4) Шаг 3 — Сценарий Reels — Хук (0–3с): «Выгорание — модное слово?»\n"
        "5) Источники — https://example.com\n"
        "6) Проверьте ссылки перед публикацией.\n" * 20
    )
    assert ra._reels_output_failed_spec(ok, "ru") is False


def test_reels_output_failed_spec_refusal_en():
    bad = (
        "Interesting topic, but I won't tear down burnout — it's not fair to sufferers. " * 20
    )
    assert ra._reels_output_failed_spec(bad, "en") is True
