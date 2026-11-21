from fastapi import APIRouter

from app.modules.vocabulary.endpoints import lecturer_vocabulary

router = APIRouter(tags=["Giảng viên - Từ vựng"])
router.include_router(lecturer_vocabulary.router)
