from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.repositories.find_user_by_id import find_user_by_id
from app.security.token_verifier import verify_access_token

ACTIVE = 1  # 1 = Hoạt động, 0 = Khóa

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Chưa đăng nhập hoặc token không hợp lệ",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    ma_nguoi_dung = verify_access_token(credentials.credentials)
    if ma_nguoi_dung is None:
        raise _unauthorized()

    user = find_user_by_id(db, ma_nguoi_dung)
    if user is None:
        raise _unauthorized()
    if user["trang_thai"] != ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa",
        )

    return {
        "ma_nguoi_dung": user["ma_nguoi_dung"],
        "ho_ten": user["ho_ten"],
        "email": user["email"],
        "vai_tro": user["vai_tro"],
    }