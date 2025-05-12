from datetime import datetime, timedelta, timezone
from jose import jwt
from app.config import settings

ALGORITHM = "HS256"


def create_access_token(subject: str, expires_delta: timedelta = None) -> str:
    exp = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode = {"exp": exp, "sub": subject}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)
