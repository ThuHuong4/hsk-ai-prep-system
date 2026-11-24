# Gom các mô-đun API, thêm tiền tố /api
from fastapi import APIRouter

from app.modules.account_profile.router import router as account_profile_router
from app.modules.admin.router import router as admin_router
from app.modules.ai_tutor.router import router as ai_tutor_router
from app.modules.auth.router import router as auth_router
from app.modules.content_reports.router import router as content_reports_router
from app.modules.exam_authoring.router import router as exam_authoring_router
from app.modules.hsk_levels.router import router as hsk_levels_router
from app.modules.lecturer_dashboard.router import router as lecturer_dashboard_router
from app.modules.materials.router import router as materials_router
from app.modules.media.router import router as media_router
from app.modules.mistake_notebook.router import router as notebook_router
from app.modules.mock_tests.router import router as mock_tests_router
from app.modules.placement.router import router as placement_router
from app.modules.practice.router import router as practice_router
from app.modules.practice_authoring.router import router as practice_authoring_router
from app.modules.questions.router import router as questions_router
from app.modules.search.router import router as search_router
from app.modules.vocabulary.router import router as vocabulary_router
from app.modules.writing_review.router import router as writing_review_router

api_router = APIRouter(prefix="/api")
api_router.include_router(hsk_levels_router)
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(questions_router)
api_router.include_router(exam_authoring_router)
api_router.include_router(media_router)
api_router.include_router(vocabulary_router)
api_router.include_router(materials_router)
api_router.include_router(practice_authoring_router)
api_router.include_router(writing_review_router)
api_router.include_router(content_reports_router)
api_router.include_router(lecturer_dashboard_router)
api_router.include_router(mock_tests_router)
api_router.include_router(placement_router)
api_router.include_router(practice_router)
api_router.include_router(notebook_router)
api_router.include_router(ai_tutor_router)
api_router.include_router(search_router)
api_router.include_router(account_profile_router)
