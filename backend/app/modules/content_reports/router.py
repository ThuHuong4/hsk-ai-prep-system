from fastapi import APIRouter

from app.modules.content_reports.endpoints import lecturer_reports

router = APIRouter(tags=["Giảng viên - Báo lỗi"])
router.include_router(lecturer_reports.router)
