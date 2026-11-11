from fastapi import APIRouter

from app.modules.auth.endpoints import (
    google_link,google_login,
    login,
    me,
    register,
    request_password_reset,
    resend_verification,
    reset_password,
    verify_email,
)

router = APIRouter(tags=["Auth"])
router.include_router(login.router)
router.include_router(me.router)
router.include_router(register.router)
router.include_router(verify_email.router)
router.include_router(resend_verification.router)
router.include_router(request_password_reset.router)
router.include_router(reset_password.router)
router.include_router(google_login.router)
router.include_router(google_link.router)