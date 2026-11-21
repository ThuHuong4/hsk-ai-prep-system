# Giảng viên soạn câu hỏi
from fastapi import APIRouter

from app.modules.questions.endpoints import lecturer_questions

router = APIRouter(tags=["Giảng viên - Câu hỏi"])
router.include_router(lecturer_questions.router)
