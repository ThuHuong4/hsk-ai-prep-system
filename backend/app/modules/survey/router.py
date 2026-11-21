from fastapi import APIRouter

from app.modules.survey.endpoints.student_survey import router as student_survey_router

router = APIRouter()
router.include_router(student_survey_router)
