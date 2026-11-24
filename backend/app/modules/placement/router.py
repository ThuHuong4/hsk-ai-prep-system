from fastapi import APIRouter

from app.modules.placement.endpoints import student_placement

router = APIRouter(tags=["Đánh giá đầu vào"])
router.include_router(student_placement.router)
