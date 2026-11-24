from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.search.services import pronounce_service, search_service

router = APIRouter(prefix="/tim-kiem")


# Công khai (Khách và người đã đăng nhập): từ vựng đã xuất bản + đề thi thử đã đăng (mục 3.2)
@router.get("")
def search(q: str = Query("", max_length=100), db: Session = Depends(get_db)):
    return search_service.search(db, q)


@router.get("/phat-am")
async def pronounce(text: str = Query(..., min_length=1, max_length=80)):
    mp3_path = await pronounce_service.get_or_create_mp3(text)
    return FileResponse(
        mp3_path,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
