# Giảng viên soạn câu hỏi
from fastapi import APIRouter

from app.modules.questions.endpoints import lecturer_assistant, lecturer_quality, lecturer_questions

router = APIRouter(tags=["Giảng viên - Câu hỏi"])
router.include_router(lecturer_questions.router)
router.include_router(lecturer_questions.group_router)
router.include_router(lecturer_assistant.router)
router.include_router(lecturer_quality.router)
