from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.exams.repositories.find_published_exam import find_published_exam

router = APIRouter()


@router.get("/exams/{ma_bo_de}")
def get_exam(
    ma_bo_de: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    exam = find_published_exam(db, ma_bo_de)
    if exam is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề thi")
    return exam