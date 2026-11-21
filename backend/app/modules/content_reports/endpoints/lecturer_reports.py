"""Giảng viên xử lý báo lỗi nội dung (mục 6.4): Mới → Đang xử lý (ghi người nhận) → Đã xử lý (kết luận + phản hồi)."""
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import ConflictError, NotFoundError, run_service
from app.modules.questions.schemas.question_payload import _clean_text
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien/bao-loi")
_NOT_FOUND = "Không tìm thấy báo lỗi"
_TABS = {
    "moi": "b.nhan_luc IS NULL",
    "dang": "b.nhan_luc IS NOT NULL AND b.xu_ly_luc IS NULL",
    "xong": "b.xu_ly_luc IS NOT NULL",
    "tat_ca": "1 = 1",
}


class ResolveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ket_luan: Literal["da_sua", "khong_phai_loi"]
    phan_hoi: str = Field(..., min_length=1, max_length=3000)

    @field_validator("phan_hoi", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)


@router.get("")
def list_reports(tab: Literal["moi", "dang", "xong", "tat_ca"] = "moi", trang: int = Query(1, ge=1),
                 so_dong: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
                 _lecturer: dict = Depends(require_lecturer)):
    base = f"""
        FROM bao_loi b
        JOIN cau_tra_loi a ON a.id = b.cau_tra_loi_id
        JOIN cau_hoi q ON q.id = a.cau_hoi_id
        LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
        JOIN luot_lam l ON l.id = a.luot_lam_id
        JOIN nguoi_dung u ON u.id = l.nguoi_dung_id
        LEFT JOIN nguoi_dung x ON x.id = b.nguoi_xu_ly_id
        LEFT JOIN cap_do cd ON cd.id = COALESCE(q.cap_do_id, p.cap_do_id)
        WHERE b.loai = 'noi_dung' AND {_TABS[tab]}
    """
    total = db.execute(text(f"SELECT COUNT(*) {base}")).scalar_one()
    rows = db.execute(
        text(f"""
            SELECT b.id, b.ly_do, b.tao_luc, b.nhan_luc, b.xu_ly_luc, b.ket_luan, b.phan_hoi,
                   u.ho_ten AS hoc_vien, x.ho_ten AS nguoi_xu_ly, b.nguoi_xu_ly_id,
                   q.id AS cau_hoi_id, q.ma_goc_id AS ma_cau, q.phien_ban, q.dang,
                   COALESCE(p.id, q.id) AS cau_soan_id,
                   LEFT(COALESCE(q.noi_dung, p.noi_dung, ''), 160) AS noi_dung_cau,
                   COALESCE(q.ky_nang, p.ky_nang) AS ky_nang, cd.ten AS ten_cap_do
            {base}
            ORDER BY b.tao_luc DESC
            LIMIT :limit OFFSET :offset
        """),
        {"limit": so_dong, "offset": (trang - 1) * so_dong},
    ).mappings().all()
    return {"tong": int(total), "muc": [dict(r) for r in rows]}


def _lock(db: Session, bao_loi_id: int) -> dict:
    row = db.execute(
        text("SELECT id, nguoi_xu_ly_id, nhan_luc, xu_ly_luc FROM bao_loi WHERE id = :id AND loai = 'noi_dung' FOR UPDATE"),
        {"id": bao_loi_id},
    ).mappings().first()
    if row is None:
        db.rollback()
        raise NotFoundError()
    return dict(row)


@router.post("/{bao_loi_id}/nhan")
def claim(bao_loi_id: int = Path(..., ge=1), db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    uid = lecturer["ma_nguoi_dung"]

    def action():
        row = _lock(db, bao_loi_id)
        if row["xu_ly_luc"] is not None:
            db.rollback()
            raise ConflictError("Báo lỗi đã được xử lý")
        if row["nguoi_xu_ly_id"] and row["nguoi_xu_ly_id"] != uid:
            db.rollback()
            raise ConflictError("Báo lỗi đang do giảng viên khác xử lý")
        db.execute(text("UPDATE bao_loi SET nguoi_xu_ly_id = :u, nhan_luc = COALESCE(nhan_luc, NOW()) WHERE id = :id"),
                   {"u": uid, "id": bao_loi_id})
        db.commit()
    run_service(action, _NOT_FOUND)
    return {"message": "Đã nhận xử lý"}


@router.post("/{bao_loi_id}/xu-ly")
def resolve(body: ResolveIn, bao_loi_id: int = Path(..., ge=1), db: Session = Depends(get_db),
            lecturer: dict = Depends(require_lecturer)):
    uid = lecturer["ma_nguoi_dung"]

    def action():
        row = _lock(db, bao_loi_id)
        if row["xu_ly_luc"] is not None:
            db.rollback()
            raise ConflictError("Báo lỗi đã được xử lý; phản hồi cũ không bị ghi đè")
        if row["nguoi_xu_ly_id"] and row["nguoi_xu_ly_id"] != uid:
            db.rollback()
            raise ConflictError("Báo lỗi đang do giảng viên khác xử lý")
        db.execute(
            text("""
                UPDATE bao_loi SET nguoi_xu_ly_id = :u, nhan_luc = COALESCE(nhan_luc, NOW()), xu_ly_luc = NOW(),
                       ket_luan = :kl, phan_hoi = :ph
                WHERE id = :id
            """),
            {"u": uid, "kl": body.ket_luan, "ph": body.phan_hoi, "id": bao_loi_id},
        )
        db.commit()
    run_service(action, _NOT_FOUND)
    return {"message": "Đã xử lý và gửi phản hồi cho học viên"}
