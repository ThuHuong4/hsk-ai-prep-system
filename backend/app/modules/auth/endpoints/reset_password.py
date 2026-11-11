from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.schemas.reset_password_request import ResetPasswordRequest
from app.modules.auth.services.reset_password import (
    ExpiredTokenError,
    InvalidTokenError,
    TokenAlreadyUsedError,
    reset_password,
)

router = APIRouter()


@router.post("/auth/reset-password")
def post_reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        reset_password(db, body.token, body.password)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"ma_loi": "TOKEN_KHONG_HOP_LE", "thong_bao": "Liên kết đặt lại mật khẩu không hợp lệ."},
        )
    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "ma_loi": "TOKEN_HET_HAN",
                "thong_bao": "Liên kết đặt lại mật khẩu đã hết hạn hoặc đã được thay bằng liên kết mới.",
            },
        )
    except TokenAlreadyUsedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"ma_loi": "TOKEN_DA_DUNG", "thong_bao": "Liên kết đặt lại mật khẩu đã được sử dụng."},
        )
    return {"message": "Đặt lại mật khẩu thành công. Hãy đăng nhập bằng mật khẩu mới."}