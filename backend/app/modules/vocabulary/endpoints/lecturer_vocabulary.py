"""Giảng viên quản lý từ vựng: thêm, sửa, tìm, nháp → xuất bản → ngừng xuất bản, nhập hàng loạt."""
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import is_duplicate_key
from app.database.session import get_db
from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError, run_service
from app.modules.questions.schemas.question_payload import _clean_media, _clean_text
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien/tu-vung")
_NOT_FOUND = "Không tìm thấy từ vựng"


class WordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chu_han: str = Field(..., min_length=1, max_length=20)
    pinyin: str = Field(..., min_length=1, max_length=60)
    nghia: str = Field(..., min_length=1, max_length=255)
    cap_do_id: int = Field(..., ge=1)
    vd_cau: str | None = Field(None, max_length=1000)
    vd_pinyin: str | None = Field(None, max_length=1000)
    vd_nghia: str | None = Field(None, max_length=1000)
    vd_audio: str | None = Field(None, max_length=255)

    @field_validator("chu_han", "pinyin", "nghia", "vd_cau", "vd_pinyin", "vd_nghia", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)

    @field_validator("vd_audio", mode="before")
    @classmethod
    def _media(cls, value):
        return _clean_media(value)


class WordImportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tu: list[WordIn] = Field(..., min_length=1, max_length=500)


_FIELDS = ("chu_han", "pinyin", "nghia", "cap_do_id", "vd_cau", "vd_pinyin", "vd_nghia", "vd_audio")


def _check_example(word: WordIn) -> None:
    if (word.vd_pinyin or word.vd_nghia or word.vd_audio) and not word.vd_cau:
        raise RuleError("Nhập câu ví dụ trước khi thêm pinyin, nghĩa hoặc audio của ví dụ")


def _check_level(db: Session, cap_do_id: int) -> None:
    if not db.execute(text("SELECT EXISTS(SELECT 1 FROM cap_do WHERE id = :id)"), {"id": cap_do_id}).scalar_one():
        raise RuleError("Cấp độ không tồn tại")


@router.get("")
def list_words(
    cap_do_id: int | None = Query(None, ge=1),
    trang_thai: Literal["nhap", "xuat_ban", "ngung_xuat_ban"] | None = None,
    q: str | None = Query(None, max_length=100),
    trang: int = Query(1, ge=1),
    so_dong: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    _lecturer: dict = Depends(require_lecturer),
):
    where, params = ["1 = 1"], {"limit": so_dong, "offset": (trang - 1) * so_dong}
    if cap_do_id:
        where.append("t.cap_do_id = :cap")
        params["cap"] = cap_do_id
    if trang_thai:
        where.append("t.trang_thai = :tt")
        params["tt"] = trang_thai
    if q and q.strip():
        where.append("(t.chu_han LIKE :q OR t.pinyin LIKE :q OR t.nghia LIKE :q)")
        params["q"] = f"%{q.strip()}%"
    condition = " AND ".join(where)
    total = db.execute(text(f"SELECT COUNT(*) FROM tu_vung t WHERE {condition}"), params).scalar_one()
    rows = db.execute(
        text(f"""
            SELECT t.id, t.chu_han, t.pinyin, t.nghia, t.cap_do_id, cd.ten AS ten_cap_do,
                   t.vd_cau, t.vd_pinyin, t.vd_nghia, t.vd_audio, t.trang_thai, t.tao_luc,
                   (SELECT COUNT(*) FROM cau_hoi q WHERE q.tu_vung_id = t.id) AS so_cau_hoi,
                   (SELECT u.ho_ten FROM nguoi_dung u WHERE u.id = t.nguoi_tao_id) AS nguoi_tao
            FROM tu_vung t JOIN cap_do cd ON cd.id = t.cap_do_id
            WHERE {condition}
            ORDER BY cd.thu_tu, t.id DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    ).mappings().all()
    return {"tong": int(total), "muc": [dict(r) for r in rows]}


def _insert(db: Session, word: WordIn, uid: int) -> int:
    params = {f: getattr(word, f) for f in _FIELDS}
    params["uid"] = uid
    result = db.execute(
        text(f"""
            INSERT INTO tu_vung ({", ".join(_FIELDS)}, trang_thai, nguoi_tao_id)
            VALUES ({", ".join(":" + f for f in _FIELDS)}, 'nhap', :uid)
        """),
        params,
    )
    return int(result.lastrowid)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_word(body: WordIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    def action():
        _check_example(body)
        _check_level(db, body.cap_do_id)
        try:
            new_id = _insert(db, body, lecturer["ma_nguoi_dung"])
            db.commit()
            return new_id
        except IntegrityError as error:
            db.rollback()
            if is_duplicate_key(error, "uq_tu_vung"):
                raise ConflictError("Từ này (cùng chữ Hán và pinyin) đã có") from error
            raise
    return {"id": run_service(action), "message": "Đã lưu từ ở trạng thái nháp"}


@router.put("/{tu_vung_id}")
def update_word(body: WordIn, tu_vung_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                _lecturer: dict = Depends(require_lecturer)):
    def action():
        _check_example(body)
        _check_level(db, body.cap_do_id)
        exists = db.execute(text("SELECT id FROM tu_vung WHERE id = :id FOR UPDATE"), {"id": tu_vung_id}).first()
        if not exists:
            db.rollback()
            raise NotFoundError()
        params = {f: getattr(body, f) for f in _FIELDS}
        params["id"] = tu_vung_id
        try:
            db.execute(text(f"UPDATE tu_vung SET {', '.join(f'{f} = :{f}' for f in _FIELDS)} WHERE id = :id"), params)
            db.commit()
        except IntegrityError as error:
            db.rollback()
            if is_duplicate_key(error, "uq_tu_vung"):
                raise ConflictError("Từ này (cùng chữ Hán và pinyin) đã có") from error
            raise
    run_service(action, _NOT_FOUND)
    return {"message": "Đã lưu từ"}


@router.post("/nhap-hang-loat", status_code=status.HTTP_201_CREATED)
def import_words(body: WordImportIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    """Nhập nhiều từ (nháp). Từ trùng chữ Hán + pinyin thì bỏ qua và báo lại."""
    def action():
        levels = {int(x) for x in db.execute(text("SELECT id FROM cap_do")).scalars().all()}
        created, skipped = 0, []
        try:
            for index, word in enumerate(body.tu, start=1):
                if word.cap_do_id not in levels:
                    raise RuleError(f"Dòng {index}: cấp độ không tồn tại")
                _check_example(word)
                exists = db.execute(
                    text("SELECT 1 FROM tu_vung WHERE chu_han = :c AND pinyin = :p"),
                    {"c": word.chu_han, "p": word.pinyin},
                ).first()
                if exists:
                    skipped.append(f"{word.chu_han} ({word.pinyin})")
                    continue
                _insert(db, word, lecturer["ma_nguoi_dung"])
                created += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
        return created, skipped
    created, skipped = run_service(action)
    message = f"Đã nhập {created} từ (nháp)"
    if skipped:
        message += f"; bỏ qua {len(skipped)} từ đã có"
    return {"message": message, "da_nhap": created, "bo_qua": skipped[:50]}


@router.post("/{tu_vung_id}/{action_name}")
def change_word_status(action_name: Literal["xuat-ban", "ngung"], tu_vung_id: int = Path(..., ge=1),
                       db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    target = {"xuat-ban": "xuat_ban", "ngung": "ngung_xuat_ban"}[action_name]
    allowed_from = {"xuat_ban": ("nhap", "ngung_xuat_ban"), "ngung_xuat_ban": ("xuat_ban",)}[target]

    def action():
        current = db.execute(text("SELECT trang_thai FROM tu_vung WHERE id = :id FOR UPDATE"), {"id": tu_vung_id}).scalar_one_or_none()
        if current is None:
            db.rollback()
            raise NotFoundError()
        if current not in allowed_from:
            db.rollback()
            raise ConflictError("Trạng thái hiện tại không cho phép thao tác này")
        db.execute(text("UPDATE tu_vung SET trang_thai = :s WHERE id = :id"), {"s": target, "id": tu_vung_id})
        db.commit()
    run_service(action, _NOT_FOUND)
    return {"message": "Đã xuất bản từ" if target == "xuat_ban" else "Đã ngừng xuất bản từ"}


@router.delete("/{tu_vung_id}")
def delete_word(tu_vung_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                _lecturer: dict = Depends(require_lecturer)):
    def action():
        current = db.execute(text("SELECT trang_thai FROM tu_vung WHERE id = :id FOR UPDATE"), {"id": tu_vung_id}).scalar_one_or_none()
        if current is None:
            db.rollback()
            raise NotFoundError()
        if current != "nhap":
            db.rollback()
            raise ConflictError("Chỉ xóa được từ nháp; từ đã xuất bản thì ngừng xuất bản")
        if db.execute(text("SELECT EXISTS(SELECT 1 FROM cau_hoi WHERE tu_vung_id = :id)"), {"id": tu_vung_id}).scalar_one():
            db.rollback()
            raise ConflictError("Từ đã được gắn vào câu hỏi, không xóa được")
        db.execute(text("DELETE FROM tu_vung WHERE id = :id"), {"id": tu_vung_id})
        db.commit()
    run_service(action, _NOT_FOUND)
    return {"message": "Đã xóa từ nháp"}
