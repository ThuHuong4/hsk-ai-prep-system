# 	Đăng ký API của mô-đun cấp HSK
from fastapi import APIRouter

from app.modules.hsk_levels.endpoints import list_hsk_levels

router = APIRouter(tags=["HSK Levels"])
router.include_router(list_hsk_levels.router)