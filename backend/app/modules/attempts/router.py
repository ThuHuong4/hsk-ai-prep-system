from fastapi import APIRouter

from app.modules.attempts.endpoints import save_answer, start_attempt
router = APIRouter(tags=["Attempts"])
router.include_router(start_attempt.router)
router.include_router(save_answer.router)