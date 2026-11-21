from fastapi import APIRouter

from app.modules.writing_review.endpoints import lecturer_writing

router = APIRouter(tags=["Giảng viên - Chấm Viết"])
router.include_router(lecturer_writing.router)
