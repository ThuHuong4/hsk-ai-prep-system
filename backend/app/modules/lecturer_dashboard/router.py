from fastapi import APIRouter

from app.modules.lecturer_dashboard.endpoints import overview

router = APIRouter(tags=["Giảng viên - Tổng quan"])
router.include_router(overview.router)
