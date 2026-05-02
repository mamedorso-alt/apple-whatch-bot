from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_token
from app.db.models import User
from app.db.session import get_db


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    raw_token = authorization.replace("Bearer ", "", 1).strip()
    token_hash = hash_token(raw_token)
    user = db.query(User).filter(User.api_token_hash == token_hash).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return user
