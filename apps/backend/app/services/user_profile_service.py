from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import User, UserBodyMetric, UserProfile, UserSubjectiveDaily


def get_or_create_profile(db: Session, user: User) -> UserProfile:
    row = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if row:
        return row
    row = UserProfile(user_id=user.id, medical_flags_json={})
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def profile_to_read(model: UserProfile) -> dict:
    flags = model.medical_flags_json or {}
    return {
        "height_cm": model.height_cm,
        "sex": model.sex,
        "birth_year": model.birth_year,
        "goal_type": model.goal_type,
        "goal_target_weight_kg": model.goal_target_weight_kg,
        "goal_horizon_date": model.goal_horizon_date,
        "diet_notes": model.diet_notes,
        "medical_flags": {
            "chronic_condition": bool(flags.get("chronic_condition")),
            "pregnancy": bool(flags.get("pregnancy")),
            "takes_medications": bool(flags.get("takes_medications")),
        },
        "quiet_hours_start": model.quiet_hours_start,
        "quiet_hours_end": model.quiet_hours_end,
        "weekly_weigh_in_weekday": model.weekly_weigh_in_weekday,
        "last_weight_kg": model.last_weight_kg,
        "last_weight_at": model.last_weight_at,
        "max_alerts_per_day": model.max_alerts_per_day,
        "food_logging_enabled": model.food_logging_enabled,
    }


def update_profile_fields(db: Session, profile: UserProfile, data: dict) -> UserProfile:
    if "height_cm" in data and data["height_cm"] is not None:
        profile.height_cm = data["height_cm"]
    if "sex" in data and data["sex"] is not None:
        profile.sex = data["sex"]
    if "birth_year" in data and data["birth_year"] is not None:
        profile.birth_year = data["birth_year"]
    if "goal_type" in data and data["goal_type"] is not None:
        profile.goal_type = data["goal_type"]
    if "goal_target_weight_kg" in data and data["goal_target_weight_kg"] is not None:
        profile.goal_target_weight_kg = data["goal_target_weight_kg"]
    if "goal_horizon_date" in data and data["goal_horizon_date"] is not None:
        profile.goal_horizon_date = data["goal_horizon_date"]
    if "diet_notes" in data and data["diet_notes"] is not None:
        profile.diet_notes = data["diet_notes"]
    if data.get("medical_flags") is not None:
        mf = data["medical_flags"]
        if hasattr(mf, "model_dump"):
            mf = mf.model_dump()
        profile.medical_flags_json = {
            "chronic_condition": bool(mf.get("chronic_condition")),
            "pregnancy": bool(mf.get("pregnancy")),
            "takes_medications": bool(mf.get("takes_medications")),
        }
    if "quiet_hours_start" in data and data["quiet_hours_start"] is not None:
        profile.quiet_hours_start = data["quiet_hours_start"]
    if "quiet_hours_end" in data and data["quiet_hours_end"] is not None:
        profile.quiet_hours_end = data["quiet_hours_end"]
    if "weekly_weigh_in_weekday" in data and data["weekly_weigh_in_weekday"] is not None:
        profile.weekly_weigh_in_weekday = data["weekly_weigh_in_weekday"]
    if "max_alerts_per_day" in data and data["max_alerts_per_day"] is not None:
        profile.max_alerts_per_day = data["max_alerts_per_day"]
    if "food_logging_enabled" in data and data["food_logging_enabled"] is not None:
        profile.food_logging_enabled = data["food_logging_enabled"]
    db.commit()
    db.refresh(profile)
    return profile


def record_weight(db: Session, user: User, weight_kg: Decimal, recorded_at: datetime | None = None) -> UserProfile:
    profile = get_or_create_profile(db, user)
    at = recorded_at or datetime.now(timezone.utc)
    db.add(UserBodyMetric(user_id=user.id, weight_kg=weight_kg, recorded_at=at, source="manual"))
    profile.last_weight_kg = weight_kg
    profile.last_weight_at = at
    db.commit()
    db.refresh(profile)
    return profile


def upsert_subjective(db: Session, user: User, day, stress: int | None, fatigue: int | None, note: str | None) -> UserSubjectiveDaily:
    row = db.query(UserSubjectiveDaily).filter(UserSubjectiveDaily.user_id == user.id, UserSubjectiveDaily.date == day).first()
    if row:
        row.stress_0_5 = stress
        row.fatigue_0_5 = fatigue
        row.note = note
    else:
        row = UserSubjectiveDaily(user_id=user.id, date=day, stress_0_5=stress, fatigue_0_5=fatigue, note=note)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row
