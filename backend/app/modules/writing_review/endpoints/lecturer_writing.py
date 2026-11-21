from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import run_service
from app.modules.questions.schemas.question_payload import _clean_text
from app.modules.writing_review.services import review_service as svc
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien/cham-viet")
_NOT_FOUND = "Không tìm thấy bài Viết"


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ket_luan: Literal["giu_nguyen", "sua_diem"]
    diem: Decimal | None = Field(None, ge=0, max_digits=5, decimal_places=2)
    nhan_xet: str = Field(..., min_length=1, max_length=3000)
    ly_do: str | None = Field(None, max_length=2000)

    @field_validator("nhan_xet", "ly_do", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)


@router.get("")
def list_writing(tab: Literal["cho", "da", "loi", "tat_ca"] = "cho", trang: int = Query(1, ge=1),
                 so_dong: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
                 _lecturer: dict = Depends(require_lecturer)):
    return svc.list_writing(db, tab, so_dong, (trang - 1) * so_dong)


@router.get("/{cau_tra_loi_id}")
def get_writing(cau_tra_loi_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                _lecturer: dict = Depends(require_lecturer)):
    return run_service(lambda: svc.get_writing_detail(db, cau_tra_loi_id), _NOT_FOUND)


@router.post("/{cau_tra_loi_id}/nhan")
def claim(cau_tra_loi_id: int = Path(..., ge=1), db: Session = Depends(get_db),
          lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.claim_report(db, cau_tra_loi_id, lecturer["ma_nguoi_dung"]), _NOT_FOUND)
    return {"message": "Đã nhận xử lý phản ánh"}


@router.post("/{cau_tra_loi_id}/quyet-dinh")
def decide(body: DecisionIn, cau_tra_loi_id: int = Path(..., ge=1), db: Session = Depends(get_db),
           lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.decide(db, cau_tra_loi_id, body, lecturer["ma_nguoi_dung"]), _NOT_FOUND)
    return {"message": "Đã giữ nguyên điểm" if body.ket_luan == "giu_nguyen" else "Đã sửa điểm, lần chấm mới được lưu"}
