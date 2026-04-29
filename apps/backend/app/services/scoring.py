from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import DailyMetric, DailyScore


def _to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _mode_for_score(score: int) -> str:
    if score >= 75:
        return "deep_work"
    if score >= 45:
        return "normal"
    return "recovery"


def _compute_baseline(db: Session, user_id, for_date: date) -> dict[str, float | bool]:
    window_start = for_date - timedelta(days=14)
    rows = (
        db.query(DailyMetric)
        .filter(DailyMetric.user_id == user_id, DailyMetric.date < for_date, DailyMetric.date >= window_start)
        .order_by(DailyMetric.date.desc())
        .all()
    )

    hr_samples = [_to_float(r.resting_hr) for r in rows if r.resting_hr is not None]
    hrv_samples = [_to_float(r.hrv_sdnn) for r in rows if r.hrv_sdnn is not None]
    valid_days = len(rows)
    soft_mode = valid_days < 3

    return {
        "resting_hr_avg": (sum(hr_samples) / len(hr_samples)) if hr_samples else 0.0,
        "hrv_avg": (sum(hrv_samples) / len(hrv_samples)) if hrv_samples else 0.0,
        "soft_mode": soft_mode,
    }


def calculate_daily_score(db: Session, metric: DailyMetric) -> tuple[int, str, dict]:
    score = 70
    reasons: list[str] = []

    if metric.sleep_min < 360:
        score -= 20
        reasons.append("sleep_low")
    elif metric.sleep_min < 420:
        score -= 10
        reasons.append("sleep_medium")

    baseline = _compute_baseline(db, metric.user_id, metric.date)
    if not baseline["soft_mode"]:
        resting_hr = _to_float(metric.resting_hr)
        hrv_sdnn = _to_float(metric.hrv_sdnn)
        if resting_hr is not None and baseline["resting_hr_avg"] > 0:
            if resting_hr > baseline["resting_hr_avg"] * 1.08:
                score -= 10
                reasons.append("resting_hr_above_baseline")
        if hrv_sdnn is not None and baseline["hrv_avg"] > 0:
            if hrv_sdnn < baseline["hrv_avg"] * 0.88:
                score -= 12
                reasons.append("hrv_below_baseline")
    else:
        reasons.append("soft_mode_baseline")

    if metric.steps < 4000:
        score -= 8
        reasons.append("steps_low")

    if metric.active_kcal >= Decimal("250"):
        score += 5
        reasons.append("active_kcal_ok")

    score = max(0, min(100, score))
    mode = _mode_for_score(score)
    reasons_json = {"items": reasons, "soft_mode": baseline["soft_mode"]}
    return score, mode, reasons_json


def upsert_daily_score(db: Session, metric: DailyMetric) -> DailyScore:
    focus_score, mode, reasons_json = calculate_daily_score(db, metric)
    row = db.query(DailyScore).filter(DailyScore.user_id == metric.user_id, DailyScore.date == metric.date).first()
    if row is None:
        row = DailyScore(user_id=metric.user_id, date=metric.date, focus_score=focus_score, mode=mode, reasons_json=reasons_json)
        db.add(row)
    else:
        row.focus_score = focus_score
        row.mode = mode
        row.reasons_json = reasons_json
    db.commit()
    db.refresh(row)
    return row
