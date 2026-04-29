from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import generate_token, hash_token
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import DeviceAuthResponse

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/device", response_model=DeviceAuthResponse)
def auth_device(db: Session = Depends(get_db)) -> DeviceAuthResponse:
    raw_token = generate_token(32)
    user = User(api_token_hash=hash_token(raw_token))
    db.add(user)
    db.commit()
    db.refresh(user)

    return DeviceAuthResponse(user_id=user.id, api_token=raw_token)
