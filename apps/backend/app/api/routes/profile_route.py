from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.profile import SubjectiveDailyIngest, UserProfileRead, UserProfileUpdate, WeightIngest
from app.services.user_profile_service import get_or_create_profile, profile_to_read, record_weight, update_profile_fields, upsert_subjective

router = APIRouter(prefix="/v1/profile", tags=["profile"])


@router.get("", response_model=UserProfileRead)
def read_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    p = get_or_create_profile(db, current_user)
    return UserProfileRead.model_validate(profile_to_read(p))


@router.patch("", response_model=UserProfileRead)
def patch_profile(
    body: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    p = get_or_create_profile(db, current_user)
    data = body.model_dump(exclude_unset=True)
    update_profile_fields(db, p, data)
    return UserProfileRead.model_validate(profile_to_read(p))


@router.post("/weight", response_model=UserProfileRead)
def post_weight(
    body: WeightIngest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    at = body.recorded_at
    if at and at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    p = record_weight(db, current_user, body.weight_kg, at)
    return UserProfileRead.model_validate(profile_to_read(p))


@router.post("/subjective", response_model=dict)
def post_subjective(
    body: SubjectiveDailyIngest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    row = upsert_subjective(db, current_user, body.date, body.stress_0_5, body.fatigue_0_5, body.note)
    return {"status": "ok", "date": str(row.date)}
