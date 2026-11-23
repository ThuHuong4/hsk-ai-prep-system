from fastapi import APIRouter

from app.modules.practice.endpoints.guest_practice import router as guest_practice_router
from app.modules.practice.endpoints.student_practice import router as student_practice_router

router = APIRouter()
router.include_router(student_practice_router)
router.include_router(guest_practice_router)

