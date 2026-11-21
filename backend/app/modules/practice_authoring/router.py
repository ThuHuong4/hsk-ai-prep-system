from fastapi import APIRouter

from app.modules.practice_authoring.endpoints import lecturer_practice

router = APIRouter(tags=["Giảng viên - Ôn luyện"])
router.include_router(lecturer_practice.router)
