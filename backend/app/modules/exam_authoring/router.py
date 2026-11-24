# Giảng viên soạn đề thi thử
from fastapi import APIRouter

from app.modules.exam_authoring.endpoints import lecturer_exam_ai, lecturer_exam_jobs, lecturer_exams

router = APIRouter(tags=["Giảng viên - Đề thi"])
# Đặt trước: tránh đường dẫn /{bo_de_id} bắt nhầm các đường dẫn ai-...
router.include_router(lecturer_exam_jobs.router)
router.include_router(lecturer_exam_ai.router)
router.include_router(lecturer_exams.router)
