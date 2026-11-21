from fastapi import APIRouter

from app.modules.account_profile.endpoints import student_profile

router = APIRouter(tags=["Học viên - Cá nhân"])
router.include_router(student_profile.router)
