from fastapi import APIRouter, Depends

from app.modules.auth.schemas.login_response import LoginUser
from app.security.current_user import get_current_user

router = APIRouter()


@router.get("/auth/me", response_model=LoginUser)
def me(current_user: dict = Depends(get_current_user)):
    return current_user