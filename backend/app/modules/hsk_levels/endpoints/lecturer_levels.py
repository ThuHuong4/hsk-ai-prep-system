import re
from typing import Literal

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import is_duplicate_key
from app.database.session import get_db
from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError, run_service
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien/cap-do")

_CODE = re.compile(r"^[A-Z0-9_\-]{2,10}$")


class LevelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma: str = Field(..., min_length=2, max_length=10)
    ten: str = Field(..., min_length=1, max_length=50)
    thu_tu: int = Field(..., ge=1, le=99)
    diem_toi_da_thi: int = Field(..., ge=1, le=1000)
    diem_dat_thi: int = Field(..., ge=1, le=1000)

    @field_validator("ma", mode="before")
    @classmethod
    def _code(cls, value):
        value = str(value or "").strip().upper()
        if not _CODE.fullmatch(value):
            raise ValueError("Mã cấp 2–10 ký tự: chữ in hoa không dấu, số, - hoặc _")
        return value

    @field_validator("ten", mode="before")
    @classmethod
    def _name(cls, value):
        return str(value or "").strip()

    @model_validator(mode="after")
    def _scores(self):
        if self.diem_dat_thi > self.diem_toi_da_thi:
            raise ValueError("Mốc đạt không được lớn hơn tổng điểm tối đa")
        return self


_SELECT = """
    SELECT c.id, c.ma, c.ten, c.thu_tu, c.diem_toi_da_thi, c.diem_dat_thi, c.trang_thai, c.tao_luc,
           (SELECT COUNT(*) FROM cau_hoi q WHERE q.cap_do_id = c.id) AS so_cau_hoi,
           (SELECT COUNT(*) FROM bo_de b WHERE b.cap_do_id = c.id) AS so_bo_de,
           (SELECT COUNT(*) FROM tu_vung t WHERE t.cap_do_id = c.id) AS so_tu_vung,
           (SELECT COUNT(*) FROM tai_lieu d WHERE d.cap_do_id = c.id) AS so_tai_lieu
    FROM cap_do c
"""


def _duplicate(error: IntegrityError) -> str | None:
    if is_duplicate_key(error, "uq_cap_do_ma"):
        return "Mã cấp đã tồn tại"
    if is_duplicate_key(error, "uq_cap_do_thu_tu"):
        return "Thứ tự này đã có cấp khác dùng"
    return None


@router.get("")
def list_levels(db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    rows = db.execute(text(_SELECT + " ORDER BY c.thu_tu")).mappings().all()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_level(body: LevelIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    def action():
        try:
            result = db.execute(
                text("""
                    INSERT INTO cap_do (ma, ten, thu_tu, diem_toi_da_thi, diem_dat_thi, trang_thai, nguoi_tao_id)
                    VALUES (:ma, :ten, :thu_tu, :max, :pass, 'nhap', :uid)
                """),
                {"ma": body.ma, "ten": body.ten, "thu_tu": body.thu_tu, "max": body.diem_toi_da_thi,
                 "pass": body.diem_dat_thi, "uid": lecturer["ma_nguoi_dung"]},
            )
            db.commit()
            return int(result.lastrowid)
        except IntegrityError as error:
            db.rollback()
            message = _duplicate(error)
            if message:
                raise ConflictError(message) from error
            raise
    return {"id": run_service(action), "message": "Đã tạo cấp ở trạng thái nháp"}


@router.put("/{cap_do_id}")
def update_level(body: LevelIn, cap_do_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                 _lecturer: dict = Depends(require_lecturer)):
    def action():
        try:
            result = db.execute(
                text("""
                    UPDATE cap_do SET ma = :ma, ten = :ten, thu_tu = :thu_tu,
                           diem_toi_da_thi = :max, diem_dat_thi = :pass
                    WHERE id = :id
                """),
                {"id": cap_do_id, "ma": body.ma, "ten": body.ten, "thu_tu": body.thu_tu,
                 "max": body.diem_toi_da_thi, "pass": body.diem_dat_thi},
            )
            if result.rowcount == 0 and not db.execute(text("SELECT 1 FROM cap_do WHERE id = :id"), {"id": cap_do_id}).first():
                raise NotFoundError()
            db.commit()
        except IntegrityError as error:
            db.rollback()
            message = _duplicate(error)
            if message:
                raise ConflictError(message) from error
            raise
        except Exception:
            db.rollback()
            raise
    run_service(action, "Không tìm thấy cấp độ")
    return {"message": "Đã lưu cấp độ"}


@router.post("/{cap_do_id}/{action_name}")
def change_level_status(action_name: Literal["dang", "an", "hien"], cap_do_id: int = Path(..., ge=1),
                        db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    allowed = {"dang": ("nhap", "da_dang"), "an": ("da_dang", "da_an"), "hien": ("da_an", "da_dang")}
    old, new = allowed[action_name]

    def action():
        current = db.execute(text("SELECT trang_thai FROM cap_do WHERE id = :id FOR UPDATE"), {"id": cap_do_id}).scalar_one_or_none()
        if current is None:
            db.rollback()
            raise NotFoundError()
        if current != old:
            db.rollback()
            raise ConflictError("Trạng thái hiện tại không cho phép thao tác này")
        db.execute(text("UPDATE cap_do SET trang_thai = :s WHERE id = :id"), {"s": new, "id": cap_do_id})
        db.commit()
    run_service(action, "Không tìm thấy cấp độ")
    return {"message": {"dang": "Đã đăng cấp", "an": "Đã ẩn cấp", "hien": "Đã hiện lại cấp"}[action_name]}


@router.delete("/{cap_do_id}")
def delete_level(cap_do_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                 _lecturer: dict = Depends(require_lecturer)):
    def action():
        row = db.execute(text(_SELECT + " WHERE c.id = :id FOR UPDATE"), {"id": cap_do_id}).mappings().first()
        if row is None:
            db.rollback()
            raise NotFoundError()
        if row["trang_thai"] != "nhap":
            db.rollback()
            raise ConflictError("Chỉ xóa được cấp nháp; cấp đã đăng thì dùng Ẩn")
        if row["so_cau_hoi"] or row["so_bo_de"] or row["so_tu_vung"] or row["so_tai_lieu"]:
            db.rollback()
            raise ConflictError("Cấp đã có nội dung, không xóa được")
        db.execute(text("DELETE FROM cap_do WHERE id = :id"), {"id": cap_do_id})
        db.commit()
    run_service(action, "Không tìm thấy cấp độ")
    return {"message": "Đã xóa cấp nháp"}
