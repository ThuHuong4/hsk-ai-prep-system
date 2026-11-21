from fastapi import APIRouter

from app.modules.mistake_notebook.endpoints.student_notebook import router as student_notebook_router

router = APIRouter()
router.include_router(student_notebook_router)
