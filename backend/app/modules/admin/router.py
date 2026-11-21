from fastapi import APIRouter

from app.modules.admin.endpoints.admin_accounts import router as admin_accounts_router

router = APIRouter()
router.include_router(admin_accounts_router)
