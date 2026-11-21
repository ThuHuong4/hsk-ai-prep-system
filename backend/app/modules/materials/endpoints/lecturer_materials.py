from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import run_service
from app.modules.materials.services import material_service as svc
from app.modules.questions.schemas.question_payload import SKILLS, _clean_text
from app.security.require_lecturer import require_lecturer
from app.storage.private_files import resolve, save_document

router = APIRouter(prefix="/giang-vien/tai-lieu")
_NOT_FOUND = "Không tìm thấy tài liệu"
_MEDIA_TYPES = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "mp3": "audio/mpeg", "wav": "audio/wav"}
_SIGNATURES = {"pdf": [b"%PDF"], "png": [b"\x89PNG"], "jpg": [b"\xff\xd8\xff"], "jpeg": [b"\xff\xd8\xff"],
               "mp3": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"], "wav": [b"RIFF"]}


class MaterialIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten: str = Field(..., min_length=1, max_length=150)
    mo_ta: str | None = Field(None, max_length=3000)
    nguon: str | None = Field(None, max_length=255)
    cap_do_id: int | None = Field(None, ge=1)
    ky_nang: Literal[SKILLS] | None = None
    duong_dan: str = Field(..., min_length=5, max_length=255)

    @field_validator("ten", "mo_ta", "nguon", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)


@router.get("")
def list_materials(
    cap_do_id: int | None = Query(None, ge=1),
    ky_nang: Literal[SKILLS] | None = None,
    trang_thai: Literal["nhap", "da_dang", "da_an"] | None = None,
    q: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
    _lecturer: dict = Depends(require_lecturer),
):
    return svc.list_materials(db, {"cap_do_id": cap_do_id, "ky_nang": ky_nang, "trang_thai": trang_thai,
                                   "q": (q or "").strip() or None})


@router.post("/tep", status_code=status.HTTP_201_CREATED)
async def upload_document(request: Request, ten: str = Query(..., min_length=3, max_length=200),
                          _lecturer: dict = Depends(require_lecturer)):
    """Nhận tệp thô (PDF, PNG/JPG, MP3/WAV, ≤ 20 MB). Trả đường dẫn để gắn vào tài liệu."""
    ext = ten.rsplit(".", 1)[-1].lower() if "." in ten else ""
    if ext not in svc.EXT_TO_TYPE:
        raise HTTPException(status_code=422, detail="Chỉ nhận PDF, PNG, JPG, MP3, WAV")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > svc.MAX_SIZE:
        raise HTTPException(status_code=413, detail="Tệp vượt quá 20 MB")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > svc.MAX_SIZE:
            raise HTTPException(status_code=413, detail="Tệp vượt quá 20 MB")
    if not data:
        raise HTTPException(status_code=422, detail="Tệp rỗng")
    if not any(bytes(data[:8]).startswith(sig) for sig in _SIGNATURES[ext]):
        raise HTTPException(status_code=422, detail="Nội dung tệp không khớp đuôi tệp")
    relative = save_document(bytes(data), "jpg" if ext == "jpeg" else ext)
    return {"duong_dan": relative, "loai_tep": svc.EXT_TO_TYPE[ext], "kich_thuoc": len(data)}


@router.get("/{tai_lieu_id}")
def get_material(tai_lieu_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                 _lecturer: dict = Depends(require_lecturer)):
    row = svc.find_material(db, tai_lieu_id)
    if row is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    row["phien_ban_moi_nhat"] = int(db.execute(text("SELECT MAX(phien_ban) FROM tai_lieu WHERE ma_goc_id = :g"),
                                               {"g": row["ma_goc_id"]}).scalar_one())
    row.update(svc.usage(db, row["ma_goc_id"]))
    return row


@router.get("/{tai_lieu_id}/tep")
def get_material_file(tai_lieu_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                      _lecturer: dict = Depends(require_lecturer)):
    row = svc.find_material(db, tai_lieu_id)
    if row is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    try:
        path = resolve(row["duong_dan"])
    except ValueError:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp")
    return FileResponse(path, media_type=_MEDIA_TYPES[row["loai_tep"]],
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("", status_code=status.HTTP_201_CREATED)
def create_material(body: MaterialIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    new_id = run_service(lambda: svc.create_material(db, body, lecturer["ma_nguoi_dung"]))
    return {"id": new_id, "message": "Đã lưu tài liệu nháp"}


@router.put("/{tai_lieu_id}")
def update_material(body: MaterialIn, tai_lieu_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                    lecturer: dict = Depends(require_lecturer)):
    saved = run_service(lambda: svc.update_material(db, tai_lieu_id, body, lecturer["ma_nguoi_dung"]), _NOT_FOUND)
    message = "Đã lưu bản nháp" if saved == tai_lieu_id else "Đã tạo phiên bản nháp mới; bản cũ vẫn dùng đến khi đăng bản mới"
    return {"id": saved, "message": message}


@router.post("/{tai_lieu_id}/{action_name}")
def change_material_status(action_name: Literal["dang", "an", "hien"], tai_lieu_id: int = Path(..., ge=1),
                           db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.change_status(db, tai_lieu_id, action_name), _NOT_FOUND)
    return {"message": {"dang": "Đã đăng tài liệu", "an": "Đã ẩn tài liệu", "hien": "Đã hiện lại tài liệu"}[action_name]}


@router.delete("/{tai_lieu_id}")
def delete_material(tai_lieu_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                    _lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.delete_material(db, tai_lieu_id), _NOT_FOUND)
    return {"message": "Đã xóa tài liệu nháp"}
