from fastapi import APIRouter

from app.modules.ai_tutor.endpoints.student_ai_tutor import router as student_ai_tutor_router

router = APIRouter()
router.include_router(student_ai_tutor_router)