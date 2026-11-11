from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.exams.services.build_exam_preview import build_exam_preview
from app.security.require_lecturer import require_lecturer

router = APIRouter()




@router.get("/admin/exams/{ma_bo_de}/preview")
def preview_exam(
    ma_bo_de: int = Path(..., ge=1),
    db: Session = Depends(get_db),
        _lecturer: dict = Depends(require_lecturer),
):
    exam = build_exam_preview(db, ma_bo_de)
    if exam is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề thi")
    return exam