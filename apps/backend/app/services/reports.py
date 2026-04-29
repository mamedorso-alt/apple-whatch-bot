from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.models import DailyMetric, DailyScore, User


def _mode_label(mode: str, lang: str) -> str:
    if lang == "en":
        return {"deep_work": "deep work", "normal": "normal", "recovery": "recovery"}.get(mode, mode)
    return {"deep_work": "глубокий фокус", "normal": "нормальный режим", "recovery": "восстановление"}.get(mode, mode)


def compose_today_report(db: Session, user: User, day: date) -> str:
    score = db.query(DailyScore).filter(DailyScore.user_id == user.id, DailyScore.date == day).first()
    metric = db.query(DailyMetric).filter(DailyMetric.user_id == user.id, DailyMetric.date == day).first()
    lang = user.language

    if not score or not metric:
        return (
            "Данных за сегодня пока нет. Откройте приложение и запустите синхронизацию."
            if lang == "ru"
            else "No data for today yet. Open the app and run sync."
        )

    if lang == "en":
        return (
            f"Today\n"
            f"Focus score: {score.focus_score}/100\n"
            f"Mode: {_mode_label(score.mode, lang)}\n"
            f"Steps: {metric.steps}\n"
            f"Active kcal: {metric.active_kcal}\n"
            f"Sleep: {metric.sleep_min} min"
        )

    return (
        f"Сегодня\n"
        f"Focus score: {score.focus_score}/100\n"
        f"Режим: {_mode_label(score.mode, lang)}\n"
        f"Шаги: {metric.steps}\n"
        f"Активные ккал: {metric.active_kcal}\n"
        f"Сон: {metric.sleep_min} мин"
    )


def compose_week_report(db: Session, user: User, end_date: date) -> str:
    start = end_date - timedelta(days=6)
    scores = (
        db.query(DailyScore)
        .filter(DailyScore.user_id == user.id, DailyScore.date >= start, DailyScore.date <= end_date)
        .order_by(DailyScore.date.asc())
        .all()
    )
    lang = user.language
    if not scores:
        return (
            "Недостаточно данных за 7 дней. Синхронизируйте приложение."
            if lang == "ru"
            else "Not enough data for the last 7 days. Please sync the app."
        )

    avg = round(sum(s.focus_score for s in scores) / len(scores))
    best = max(scores, key=lambda s: s.focus_score)
    worst = min(scores, key=lambda s: s.focus_score)
    trend_delta = scores[-1].focus_score - scores[0].focus_score if len(scores) > 1 else 0
    trend = (
        ("up", f"+{trend_delta}")
        if trend_delta > 0
        else ("down", str(trend_delta))
        if trend_delta < 0
        else ("flat", "0")
    )
    recommendation_en = (
        "Keep current rhythm and protect deep-focus hours."
        if avg >= 75
        else "Stabilize sleep and add one extra movement block daily."
        if avg >= 45
        else "Use recovery mode: lower load and prioritize sleep."
    )
    recommendation_ru = (
        "Сохраняйте текущий ритм и защищайте часы глубокого фокуса."
        if avg >= 75
        else "Стабилизируйте сон и добавьте еще один блок движения в день."
        if avg >= 45
        else "Выберите режим восстановления: меньше нагрузки и больше сна."
    )

    if lang == "en":
        return (
            f"Week summary\n"
            f"Average focus score: {avg}/100\n"
            f"Best day: {best.date} ({best.focus_score})\n"
            f"Lowest day: {worst.date} ({worst.focus_score})\n"
            f"Trend: {trend[0]} ({trend[1]})\n"
            f"Days with data: {len(scores)}/7\n"
            f"Recommendation: {recommendation_en}"
        )

    return (
        f"Итоги недели\n"
        f"Средний focus score: {avg}/100\n"
        f"Лучший день: {best.date} ({best.focus_score})\n"
        f"Самый слабый день: {worst.date} ({worst.focus_score})\n"
        f"Тренд: {trend[0]} ({trend[1]})\n"
        f"Дней с данными: {len(scores)}/7\n"
        f"Рекомендация: {recommendation_ru}"
    )
