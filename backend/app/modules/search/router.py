from fastapi import APIRouter

from app.modules.search.endpoints import public_search

router = APIRouter(tags=["Tìm kiếm"])
router.include_router(public_search.router)
