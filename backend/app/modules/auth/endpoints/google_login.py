from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.integrations.google.id_token_verifier import (
    GoogleServiceUnavailableError,
    InvalidGoogleTokenError,
    verify_google_id_token,
)
from app.modules.auth.schemas.login_response import LoginResponse
from app.modules.auth.services.authenticate_user import AccountLockedError
from app.modules.auth.services.login_with_google import (
    AccountLinkRequiredError,
    GoogleEmailNotVerifiedError,
    login_with_google,
)
from app.security.token_issuer import create_access_token

router = APIRouter()


class GoogleLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credential: str = Field(..., min_length=20, max_length=4096)


@router.post("/auth/google", response_model=LoginResponse)
def google_login(body: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        identity = verify_google_id_token(body.credential)
    except InvalidGoogleTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"ma_loi": "GOOGLE_TOKEN_KHONG_HOP_LE", "thong_bao": "Không xác thực được tài khoản Google. Vui lòng thử lại."},
        )
    except GoogleServiceUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không kết nối được Google, vui lòng thử lại sau",
        )

    try:
        user = login_with_google(db, identity)
    except GoogleEmailNotVerifiedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"ma_loi": "GOOGLE_EMAIL_CHUA_XAC_MINH", "thong_bao": "Email của tài khoản Google chưa được Google xác minh."},
        )
    except AccountLinkRequiredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "ma_loi": "CAN_LIEN_KET_TAI_KHOAN",
                "thong_bao": (
                    "Email này đã có tài khoản HSK AI. Hãy đăng nhập bằng mật khẩu "
                    "(hoặc dùng Quên mật khẩu) để xác nhận trước khi liên kết Google."
                ),
            },
        )
    except AccountLockedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")

    return LoginResponse(access_token=create_access_token(user["ma_nguoi_dung"]), user=user)