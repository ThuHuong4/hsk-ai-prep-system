"""Kiểm định chất lượng câu hỏi bằng dữ liệu làm bài thật và kiểm tra trùng lặp nội dung."""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.questions.services.quality_service import find_similar, item_quality
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien")


class SimilarIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    noi_dung: str = Field(..., max_length=5000)
    cap_do_id: int = Field(..., ge=1)
    dang: str = Field(..., max_length=20)
    bo_qua_ma_goc: int | None = Field(None, ge=1)  # khi sửa câu: không so với chính nó


@router.get("/chat-luong-cau-hoi")
def get_item_quality(
    cap_do_id: int | None = Query(None, ge=1),
    ky_nang: Literal["nghe", "doc", "viet", "tu_vung"] | None = None,
    chi_canh_bao: bool = True,
    db: Session = Depends(get_db),
    _lecturer: dict = Depends(require_lecturer),
):
    return item_quality(db, cap_do_id, ky_nang, chi_canh_bao)


@router.post("/cau-hoi-trung")
def post_similar(body: SimilarIn, db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    return {"trung_lap": find_similar(db, [body.model_dump()])[0]}
