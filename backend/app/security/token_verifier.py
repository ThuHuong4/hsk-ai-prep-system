import jwt

from app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY


def verify_access_token(token: str) -> int | None:
    """Trả ma_nguoi_dung nếu token hợp lệ, ngược lại trả None."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
        ma_nguoi_dung = int(payload["sub"])
    except (jwt.PyJWTError, TypeError, ValueError):
        return None
    return ma_nguoi_dung if ma_nguoi_dung > 0 else None