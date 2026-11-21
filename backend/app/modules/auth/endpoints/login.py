#nhận yêu cầu đăng nhập từ frontend, kiểm tra email và mật khẩu, trả về kết quả
# importt để lấy công cụ cần dùng
# APIRouter: tạo đường dẫn 

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.schemas.login_request import LoginRequest
from app.modules.auth.schemas.login_response import LoginResponse
from app.modules.auth.services.authenticate_user import (
    AccountLockedError,
    InvalidCredentialsError,
    authenticate_user,
)
from app.security.token_issuer import create_access_token

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, body.email, body.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng. Nếu bạn đã đăng ký bằng Google, hãy chọn Đăng nhập với Google.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AccountLockedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa",
        )
    return LoginResponse(
        access_token=create_access_token(user["ma_nguoi_dung"]),
        user=user,
    )