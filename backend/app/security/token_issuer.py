from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY


def create_access_token(ma_nguoi_dung: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(ma_nguoi_dung),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)