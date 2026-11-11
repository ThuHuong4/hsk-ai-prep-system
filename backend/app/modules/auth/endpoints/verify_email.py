from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.services.verify_email import (
    ExpiredTokenError,
    InvalidTokenError,
    TokenAlreadyUsedError,
    verify_email,
)

router = APIRouter()


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=1, max_length=128)


@router.post("/auth/verify-email")
def post_verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    try:
        verify_email(db, body.token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"ma_loi": "TOKEN_KHONG_HOP_LE", "thong_bao": "Liên kết xác minh không hợp lệ."},
        )
    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "ma_loi": "TOKEN_HET_HAN",
                "thong_bao": "Liên kết xác minh đã hết hạn hoặc đã được thay bằng liên kết mới. Hãy yêu cầu gửi lại.",
            },
        )
    except TokenAlreadyUsedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"ma_loi": "TOKEN_DA_DUNG", "thong_bao": "Email đã được xác minh trước đó. Bạn có thể đăng nhập."},
        )
    return {"message": "Xác minh email thành công. Bạn có thể đăng nhập."}