from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import DailyMetric, User, UserProfile


@dataclass
class BaselineBundle:
    median_steps: float | None
    median_active_kcal: float | None
    median_sleep_min: float | None
    days_count: int


def _median(vals: list[float]) -> float | None:
    clean = [v for v in vals if v is not None and v >= 0]
    if len(clean) < 3:
        return None
    return float(statistics.median(clean))


def compute_baselines(metrics: list[DailyMetric]) -> BaselineBundle:
    if not metrics:
        return BaselineBundle(None, None, None, 0)
    steps = [float(m.steps) for m in metrics]
    kcals = [float(m.active_kcal) for m in metrics]
    sleeps = [float(m.sleep_min) for m in metrics if m.sleep_min and m.sleep_min > 0]
    return BaselineBundle(
        median_steps=_median(steps),
        median_active_kcal=_median(kcals),
        median_sleep_min=_median(sleeps) if len(sleeps) >= 3 else None,
        days_count=len(metrics),
    )


def sleep_regularity_score(metrics: list[DailyMetric], days: int = 14) -> float | None:
    ends: list[datetime] = []
    for m in metrics:
        if m.sleep_end is None:
            continue
        ends.append(m.sleep_end)
    if len(ends) < 4:
        return None
    by_date = {m.date: m.sleep_end for m in metrics if m.sleep_end is not None}
    sorted_dates = sorted(by_date.keys())
    recent = sorted_dates[-days:] if len(sorted_dates) > days else sorted_dates
    if len(recent) < 4:
        return None
    minutes_from_midnight = []
    for d in recent:
        dt = by_date[d]
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        minutes_from_midnight.append(dt.hour * 60 + dt.minute + dt.second / 60.0)
    med = statistics.median(minutes_from_midnight)
    mad = statistics.median([abs(x - med) for x in minutes_from_midnight])
    if mad < 1:
        return 100.0
    score = max(0.0, 100.0 - mad * 0.7)
    return round(score, 1)


def load_recent_metrics(db: Session, user_id, end_date: date, days: int) -> list[DailyMetric]:
    start = end_date - timedelta(days=days - 1)
    return (
        db.query(DailyMetric)
        .filter(DailyMetric.user_id == user_id, DailyMetric.date >= start, DailyMetric.date <= end_date)
        .order_by(DailyMetric.date.asc())
        .all()
    )


def build_daily_insight_text(db: Session, user: User, today: date, lang: str) -> str:
    cfg = get_settings()
    metrics = load_recent_metrics(db, user.id, today, cfg.insights_baseline_days)
    base = compute_baselines(metrics[:-1] if len(metrics) > 1 else metrics)
    today_m = next((m for m in reversed(metrics) if m.date == today), None)
    reg = sleep_regularity_score(metrics, days=cfg.insights_regularity_days)

    lines: list[str] = []
    if lang == "en":
        lines.append("Daily insight (informational, not medical advice).")
        if base.median_sleep_min and today_m and today_m.sleep_min:
            ratio = today_m.sleep_min / base.median_sleep_min if base.median_sleep_min else 1
            if ratio < 0.85:
                lines.append(f"Sleep today ({today_m.sleep_min} min) is below your recent median (~{int(base.median_sleep_min)} min).")
            elif ratio > 1.1:
                lines.append("Sleep today is above your usual — recovery window looks wider.")
        if base.median_steps and today_m:
            if today_m.steps < 0.7 * base.median_steps:
                lines.append(f"Steps are below your baseline (~{int(base.median_steps)}). A short walk can help.")
        if reg is not None:
            lines.append(f"Sleep regularity score (last days): {reg}/100.")
        if not lines or len(lines) == 1:
            lines.append("Keep syncing — more days improve baselines and tips.")
    else:
        lines.append("Краткий инсайт дня (информация, не медсовет).")
        if base.median_sleep_min and today_m and today_m.sleep_min:
            ratio = today_m.sleep_min / base.median_sleep_min if base.median_sleep_min else 1
            if ratio < 0.85:
                lines.append(f"Сон сегодня ({today_m.sleep_min} мин) ниже вашей медианы (~{int(base.median_sleep_min)} мин).")
            elif ratio > 1.1:
                lines.append("Сон сегодня выше обычного — хороший запас восстановления.")
        if base.median_steps and today_m:
            if today_m.steps < 0.7 * base.median_steps:
                lines.append(f"Шаги ниже базы (~{int(base.median_steps)}). Короткая прогулка уже полезна.")
        if reg is not None:
            lines.append(f"Оценка регулярности сна (последние дни): {reg}/100.")
        if not lines or len(lines) == 1:
            lines.append("Продолжайте синк — чем больше дней данных, тем точнее подсказки.")

    return "\n".join(lines)


def build_weekly_trend_text(db: Session, user: User, today: date, lang: str) -> str:
    this_week = load_recent_metrics(db, user.id, today, 7)
    prev_end = today - timedelta(days=7)
    prev_week = load_recent_metrics(db, user.id, prev_end, 7)

    def avg_sleep(ms: list[DailyMetric]) -> float | None:
        ss = [m.sleep_min for m in ms if m.sleep_min > 0]
        return sum(ss) / len(ss) if len(ss) >= 2 else None

    def avg_steps(ms: list[DailyMetric]) -> float | None:
        if len(ms) < 2:
            return None
        return sum(m.steps for m in ms) / len(ms)

    s1, s2 = avg_sleep(this_week), avg_sleep(prev_week)
    t1, t2 = avg_steps(this_week), avg_steps(prev_week)

    if lang == "en":
        parts = ["Week vs previous (approximate):"]
        if s1 and s2:
            parts.append(f"Avg sleep: {s1:.0f} min vs {s2:.0f} min ({s1 - s2:+.0f}).")
        elif s1:
            parts.append(f"Avg sleep this week: {s1:.0f} min.")
        if t1 and t2:
            parts.append(f"Avg steps: {t1:.0f} vs {t2:.0f} ({t1 - t2:+.0f}).")
        elif t1:
            parts.append(f"Avg steps this week: {t1:.0f}.")
        parts.append("Trends are noisy with little data — aim for 2+ weeks.")
        return "\n".join(parts)

    parts = ["Неделя к прошлой (приблизительно):"]
    if s1 and s2:
        parts.append(f"Средний сон: {s1:.0f} мин vs {s2:.0f} мин ({s1 - s2:+.0f}).")
    elif s1:
        parts.append(f"Средний сон за неделю: {s1:.0f} мин.")
    if t1 and t2:
        parts.append(f"Средние шаги: {t1:.0f} vs {t2:.0f} ({t1 - t2:+.0f}).")
    elif t1:
        parts.append(f"Средние шаги за неделю: {t1:.0f}.")
    parts.append("Мало данных шумит — ориентир от 2+ недель.")
    return "\n".join(parts)


def evaluate_alert_triggers(
    db: Session,
    user: User,
    today: date,
    now_utc: datetime,
) -> list[tuple[str, str]]:
    cfg = get_settings()
    metrics_28 = load_recent_metrics(db, user.id, today, cfg.insights_baseline_days)
    if len(metrics_28) < 5:
        return []
    base = compute_baselines([m for m in metrics_28 if m.date < today])
    out: list[tuple[str, str]] = []
    today_m = next((m for m in reversed(metrics_28) if m.date == today), None)
    if not today_m:
        return []

    y = today - timedelta(days=1)
    y_m = next((m for m in metrics_28 if m.date == y), None)
    if base.median_sleep_min and y_m and today_m:
        if y_m.sleep_min > 0 and today_m.sleep_min > 0:
            if y_m.sleep_min < 0.85 * base.median_sleep_min and today_m.sleep_min < 0.85 * base.median_sleep_min:
                out.append(
                    (
                        "sleep_low_2d",
                        "Сон второй день подряд заметно ниже вашей нормы. Постарайтесь лечь раньше и стабилизировать подъём.",
                    )
                )

    if base.median_steps and now_utc.hour >= 15:
        if today_m.steps < 0.55 * base.median_steps:
            out.append(
                (
                    "steps_low_evening",
                    f"Шагов сегодня меньше обычного (сейчас {today_m.steps}, база ~{int(base.median_steps)}). Короткая прогулка?",
                )
            )

    prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if prof and prof.weekly_weigh_in_weekday is not None and prof.last_weight_at:
        days_since = (now_utc.date() - prof.last_weight_at.date()).days
        if days_since >= 10:
            out.append(("weight_stale", "Давно не было веса. Отправьте /weight 72.4 (пример) для недельного трека."))

    return out


def is_quiet_hours(now_local_hour: int, now_local_minute: int, start: str | None, end: str | None) -> bool:
    if not start or not end:
        return False

    def parse_hm(s: str) -> int:
        h, m = s.split(":", 1)
        return int(h) * 60 + int(m)

    cur = now_local_hour * 60 + now_local_minute
    a, b = parse_hm(start), parse_hm(end)
    if a <= b:
        return a <= cur < b
    return cur >= a or cur < b
