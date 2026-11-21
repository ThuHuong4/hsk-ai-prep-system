from fastapi import APIRouter

from app.modules.materials.endpoints import lecturer_materials, student_materials

router = APIRouter(tags=["Tài liệu"])
router.include_router(lecturer_materials.router)
router.include_router(student_materials.router)
