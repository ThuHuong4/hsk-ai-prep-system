from fastapi import APIRouter

from app.modules.content_reports.endpoints import lecturer_reports, student_reports

router = APIRouter(tags=["Báo lỗi nội dung"])
router.include_router(lecturer_reports.router)
router.include_router(student_reports.router)
