from fastapi import APIRouter

from app.modules.media.endpoints import upload_media

router = APIRouter(tags=["Tệp đa phương tiện"])
router.include_router(upload_media.router)
