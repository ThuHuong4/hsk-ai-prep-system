from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.hsk_levels.repositories.list_hsk_levels import list_hsk_levels

router = APIRouter()


@router.get("/hsk-levels")
def get_hsk_levels(db: Session = Depends(get_db)):
    return list_hsk_levels(db)