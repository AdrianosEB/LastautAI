import os
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

SECRET = os.environ.get("AUTH_SECRET", "dev-secret-change-in-production")
ALGORITHM = "HS256"
EXPIRE_HOURS = 24


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> int | None:
    """Returns user_id or None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None
