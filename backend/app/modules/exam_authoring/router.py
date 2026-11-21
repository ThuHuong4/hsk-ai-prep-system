# Giảng viên soạn đề thi thử
from fastapi import APIRouter

from app.modules.exam_authoring.endpoints import lecturer_exams

router = APIRouter(tags=["Giảng viên - Đề thi"])
router.include_router(lecturer_exams.router)
