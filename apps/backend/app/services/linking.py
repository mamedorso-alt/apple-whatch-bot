import secrets
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import LinkCode, User

settings = get_settings()


def generate_link_code(db: Session, user: User) -> LinkCode:
    alphabet = string.ascii_uppercase + string.digits
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.link_code_ttl_min)

    for _ in range(5):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        link_code = LinkCode(user_id=user.id, code=code, expires_at=expires_at)
        db.add(link_code)
        try:
            db.commit()
            db.refresh(link_code)
            return link_code
        except IntegrityError:
            db.rollback()

    raise RuntimeError("Unable to generate unique link code")
