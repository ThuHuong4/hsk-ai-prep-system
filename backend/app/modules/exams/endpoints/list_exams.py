from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.exams.repositories.list_exams_by_level import list_exams_by_level

router = APIRouter()


@router.get("/exams")
def get_exams(
    ma_cap_do: int = Query(..., ge=1, le=4),
    db: Session = Depends(get_db),
):
    return list_exams_by_level(db, ma_cap_do)