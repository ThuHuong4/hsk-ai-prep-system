from fastapi import APIRouter

from app.modules.practice.endpoints.guest_practice import router as guest_practice_router
from app.modules.practice.endpoints.student_practice import router as student_practice_router
from app.modules.admin.router import router as admin_router
from app.modules.mistake_notebook.router import router as notebook_router
from app.modules.survey.router import router as survey_router

router = APIRouter()
router.include_router(student_practice_router)
router.include_router(guest_practice_router)
# Khảo sát đầu vào, Quản trị viên, Sổ tay & nhiệm vụ: gắn qua đây để không phải sửa api/router.py
router.include_router(survey_router)
router.include_router(admin_router)
router.include_router(notebook_router)
