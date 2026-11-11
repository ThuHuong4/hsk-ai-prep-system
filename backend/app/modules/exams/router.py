from fastapi import APIRouter

from app.modules.exams.endpoints import get_exam, list_exams, preview_exam

router = APIRouter(tags=["Exams"])
router.include_router(list_exams.router)
router.include_router(get_exam.router)
router.include_router(preview_exam.router)