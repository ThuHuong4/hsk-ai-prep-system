"""Học viên báo lỗi nội dung câu hỏi (đề sai, đáp án sai, âm thanh/hình lỗi...) và xem phản hồi của Giảng viên.

Quy tắc:
- Chỉ báo được câu trong lượt làm của chính mình, và chỉ SAU KHI câu đã được kiểm tra (Ôn luyện) hoặc lượt đã nộp
  (Thi thử): không dùng báo lỗi để dò đáp án trong lúc làm bài.
- Mỗi câu trả lời chỉ có một báo lỗi đang mở (chỉ mục duy nhất uq_bao_loi_dang_mo trong CSDL).
- Báo lỗi đổ về trang "Báo lỗi nội dung" của Giảng viên; kết luận và phản hồi hiện lại cho học viên.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import is_duplicate_key
from app.database.session import get_db
from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError, run_service
from app.modules.questions.schemas.question_payload import _clean_text
from app.security.require_student import require_student

router = APIRouter(prefix="/bao-loi")

KIND_VI = {
    "de_sai": "Đề bài sai hoặc khó hiểu",
    "dap_an_sai": "Đáp án sai",
    "nhieu_dap_an": "Có nhiều hơn một đáp án đúng",
    "am_thanh": "Âm thanh lỗi hoặc không khớp",
    "hinh_anh": "Hình ảnh lỗi",
    "giai_thich": "Giải thích chưa đúng",
    "khac": "Lỗi khác",
}


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    luot_lam_id: int = Field(..., ge=1)
    cau_hoi_id: int = Field(..., ge=1)
    loai_loi: Literal["de_sai", "dap_an_sai", "nhieu_dap_an", "am_thanh", "hinh_anh", "giai_thich", "khac"]
    mo_ta: str = Field(..., min_length=5, max_length=1000)

    @field_validator("mo_ta", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value) or ""


@router.post("")
def post_report(body: ReportIn, db: Session = Depends(get_db), student: dict = Depends(require_student)):
    uid = student["ma_nguoi_dung"]

    def action():
        row = db.execute(text("""
            SELECT a.id, a.xac_nhan_luc, l.trang_thai, l.nguoi_dung_id
            FROM cau_tra_loi a JOIN luot_lam l ON l.id = a.luot_lam_id
            WHERE a.luot_lam_id = :l AND a.cau_hoi_id = :q
        """), {"l": body.luot_lam_id, "q": body.cau_hoi_id}).mappings().first()
        if row is None or row["nguoi_dung_id"] != uid:
            raise NotFoundError()
        if row["xac_nhan_luc"] is None and row["trang_thai"] != "da_nop":
            raise RuleError("Chỉ báo lỗi sau khi câu đã được kiểm tra hoặc bài đã nộp")
        try:
            db.execute(
                text("INSERT INTO bao_loi (cau_tra_loi_id, loai, ly_do) VALUES (:a, 'noi_dung', :r)"),
                {"a": row["id"], "r": f"[{KIND_VI[body.loai_loi]}] {body.mo_ta}"},
            )
            db.commit()
        except IntegrityError as error:
            db.rollback()
            if is_duplicate_key(error, "uq_bao_loi_dang_mo"):
                raise ConflictError("Bạn đã báo lỗi câu này, Giảng viên đang xem xét") from error
            raise
    run_service(action, "Không tìm thấy câu trong lượt làm của bạn")
    return {"message": "Đã gửi báo lỗi. Giảng viên sẽ xem xét và phản hồi."}


@router.get("/cua-toi")
def my_reports(so_dong: int = Query(20, ge=1, le=50), db: Session = Depends(get_db),
               student: dict = Depends(require_student)):
    rows = db.execute(text("""
        SELECT b.id, b.ly_do, b.tao_luc, b.nhan_luc, b.xu_ly_luc, b.ket_luan, b.phan_hoi,
               LEFT(COALESCE(q.noi_dung, p.noi_dung, ''), 120) AS noi_dung_cau
        FROM bao_loi b
        JOIN cau_tra_loi a ON a.id = b.cau_tra_loi_id
        JOIN luot_lam l ON l.id = a.luot_lam_id
        JOIN cau_hoi q ON q.id = a.cau_hoi_id
        LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
        WHERE l.nguoi_dung_id = :u AND b.loai = 'noi_dung'
        ORDER BY b.tao_luc DESC LIMIT :n
    """), {"u": student["ma_nguoi_dung"], "n": so_dong}).mappings().all()
    return {"muc": [dict(r) for r in rows]}
