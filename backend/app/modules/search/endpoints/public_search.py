from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.search.services import search_service

router = APIRouter(prefix="/tim-kiem")


# Công khai (Khách và người đã đăng nhập): từ vựng đã xuất bản + đề thi thử đã đăng (mục 3.2)
@router.get("")
def search(q: str = Query("", max_length=100), db: Session = Depends(get_db)):
    return search_service.search(db, q)
