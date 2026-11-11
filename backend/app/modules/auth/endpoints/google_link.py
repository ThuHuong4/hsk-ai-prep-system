from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.named_lock import LockNotAcquiredError
from app.database.session import get_db
from app.integrations.google.id_token_verifier import (
    GoogleServiceUnavailableError,
    InvalidGoogleTokenError,
    verify_google_id_token,
)
from app.modules.auth.schemas.login_response import LoginResponse
from app.modules.auth.services.authenticate_user import AccountLockedError, InvalidCredentialsError
from app.modules.auth.services.enforce_request_limit import RateLimitedError
from app.modules.auth.services.link_google_account import (
    AccountAlreadyHasGoogleError,
    GoogleAlreadyLinkedError,
    link_google_account,
)
from app.modules.auth.services.login_with_google import GoogleEmailNotVerifiedError
from app.security.client_ip import get_client_ip
from app.security.token_issuer import create_access_token

router = APIRouter()


class GoogleLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credential: str = Field(..., min_length=20, max_length=4096)
    password: str = Field(..., min_length=1, max_length=128)


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"ma_loi": code, "thong_bao": message})


@router.post("/auth/google/link", response_model=LoginResponse)
def google_link(body: GoogleLinkRequest, request: Request, db: Session = Depends(get_db)):
    try:
        identity = verify_google_id_token(body.credential)
    except InvalidGoogleTokenError:
        raise _error(401, "GOOGLE_TOKEN_KHONG_HOP_LE",
                     "Phiên đăng nhập Google đã hết hạn hoặc không hợp lệ. Hãy bấm Đăng nhập bằng Google lại.")
    except GoogleServiceUnavailableError:
        raise HTTPException(status_code=503, detail="Không kết nối được Google, vui lòng thử lại sau")

    try:
        user = link_google_account(db, identity, body.password, get_client_ip(request))
    except RateLimitedError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Bạn đã thử quá nhiều lần, vui lòng thử lại sau")
    except LockNotAcquiredError:
        raise HTTPException(status_code=503, detail="Hệ thống đang bận, vui lòng thử lại")
    except GoogleEmailNotVerifiedError:
        raise _error(403, "GOOGLE_EMAIL_CHUA_XAC_MINH", "Email của tài khoản Google chưa được Google xác minh.")
    except InvalidCredentialsError:
        raise _error(401, "MAT_KHAU_KHONG_DUNG",
                     "Mật khẩu không đúng. Nếu quên mật khẩu, hãy dùng chức năng Quên mật khẩu.")
    except AccountLockedError:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khóa")
    except GoogleAlreadyLinkedError:
        raise _error(409, "GOOGLE_DA_LIEN_KET",
                     "Tài khoản Google này đã được liên kết. Hãy đăng nhập bằng Google.")
    except AccountAlreadyHasGoogleError:
        raise _error(409, "TAI_KHOAN_DA_CO_GOOGLE",
                     "Tài khoản HSK AI này đã liên kết với một tài khoản Google khác.")

    return LoginResponse(access_token=create_access_token(user["ma_nguoi_dung"]), user=user)