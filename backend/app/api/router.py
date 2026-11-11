# 	Gom các mô-đun API, thêm tiền tố /api
from fastapi import APIRouter

from app.modules.hsk_levels.router import router as hsk_levels_router

from app.modules.exams.router import router as exams_router
from app.modules.auth.router import router as auth_router
from app.modules.attempts.router import router as attempts_router
api_router = APIRouter(prefix="/api")
api_router.include_router(hsk_levels_router)

api_router.include_router(exams_router)
api_router.include_router(auth_router)
api_router.include_router(attempts_router)