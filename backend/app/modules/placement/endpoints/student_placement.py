"""Các điểm cuối HTTP (FastAPI Endpoints) cho Đánh giá trình độ đầu vào 8 câu của Học viên.

- Vai trò: Nhận HTTP request từ Frontend, kiểm tra xác thực vai trò Học viên (`require_student`),
  validate dữ liệu đầu vào bằng Pydantic rồi ủy quyền cho `placement_service` và `placement_analyzer`.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import run_service
from app.modules.placement.services import placement_analyzer, placement_service
from app.security.require_student import require_student

router = APIRouter(prefix="/danh-gia-dau-vao")
_NOT_FOUND = "Không tìm thấy phiên đánh giá đầu vào"


class StepSubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cau_hoi_id: int = Field(..., ge=1)
    phuong_an_chon_id: int | None = Field(None, ge=1)
    van_ban: str | None = Field(None, max_length=2000)
    bo_qua: bool = False
    thoi_gian_lam_giay: int | None = Field(None, ge=0, le=3600)


class ReplaceQuestionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ly_do: Literal["loi_audio", "loi_hinh_anh", "loi_hien_thi", "loi_noi_dung"] = "loi_audio"


class TargetGoalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cap_do_id: int | None = Field(None, ge=1)
    phut_moi_ngay: int | None = None


@router.get("/trang-thai")
def status_gate(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return placement_service.entry_gate(db, student["ma_nguoi_dung"])


@router.post("/bat-dau")
def start(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    luot_id = run_service(lambda: placement_service.start_placement(db, student["ma_nguoi_dung"]))
    return {"luot_id": luot_id}


@router.post("/de-sau")
def defer(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    placement_service.defer_placement(db, student["ma_nguoi_dung"])
    return {"da_luu": True}


@router.get("/luot/{luot_id}")
def get_attempt(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: placement_service.get_session(db, luot_id, student["ma_nguoi_dung"]), _NOT_FOUND)


@router.post("/luot/{luot_id}/tra-loi")
def answer_step(
    body: StepSubmitIn,
    luot_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    student: dict = Depends(require_student),
):
    return run_service(lambda: placement_service.submit_step(db, luot_id, student["ma_nguoi_dung"], body), _NOT_FOUND)


@router.post("/luot/{luot_id}/doi-cau")
def replace_broken(
    body: ReplaceQuestionIn,
    luot_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    student: dict = Depends(require_student),
):
    return run_service(
        lambda: placement_service.replace_broken_question(db, luot_id, student["ma_nguoi_dung"], body.ly_do),
        _NOT_FOUND,
    )


@router.post("/luot/{luot_id}/phan-tich")
def run_analysis(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: placement_analyzer.analyze_placement(db, luot_id, student["ma_nguoi_dung"]), _NOT_FOUND)


@router.get("/luot/{luot_id}/ket-qua")
def get_result(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: placement_analyzer.get_placement_result(db, luot_id, student["ma_nguoi_dung"]), _NOT_FOUND)


@router.put("/muc-tieu")
def update_goal(body: TargetGoalIn, db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(
        lambda: placement_service.save_target_level(db, student["ma_nguoi_dung"], body.cap_do_id, body.phut_moi_ngay)
    )
