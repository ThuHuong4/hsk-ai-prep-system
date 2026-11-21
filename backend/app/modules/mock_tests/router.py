from fastapi import APIRouter

from app.modules.mock_tests.endpoints import student_mock_tests, student_roadmap, student_stats

router = APIRouter(tags=["Học viên - Thi thử"])
router.include_router(student_mock_tests.router)
router.include_router(student_roadmap.router)
router.include_router(student_stats.router)
