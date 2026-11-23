"""Học viên xem Tài liệu ôn tập (mục 6.5): chỉ tài liệu đang đăng, cần đăng nhập.

Danh sách trả thông tin mô tả, không trả đường dẫn tệp; mở tệp qua GET /tai-lieu/{id}/tep (đã kiểm tra quyền và trạng thái).
Xem tài liệu không hoàn thành bài, không cộng KN, không tính nhiệm vụ.
"""
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import run_service
from app.modules.materials.services.material_service import EXTERNAL, published_material_file
from app.security.require_student import require_student
from app.storage.private_files import resolve

router = APIRouter(prefix="/tai-lieu")
_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
}


@router.get("")
def list_published(db: Session = Depends(get_db), _student: dict = Depends(require_student)):
    rows = db.execute(
        text("""
            SELECT t.id, t.ten, t.mo_ta, t.nguon, t.cap_do_id, cd.ten AS ten_cap_do, cd.thu_tu AS cap_thu_tu,
                   t.ky_nang, t.loai_tep, t.kich_thuoc, t.tao_luc
            FROM tai_lieu t LEFT JOIN cap_do cd ON cd.id = t.cap_do_id
            WHERE t.trang_thai = 'da_dang'
            ORDER BY cd.thu_tu IS NULL, cd.thu_tu, t.ten
        """)
    ).mappings().all()
    db.rollback()
    return [dict(r) for r in rows]


@router.get("/lien-ket")
def external_links(_student: dict = Depends(require_student)):
    """Nguồn học bên ngoài có tên đơn vị cụ thể: chỉ dẫn liên kết, không lưu/tải lại nội dung."""
    return [
        {"ten": x["ten"], "mo_ta": x["mo_ta"], "url": x["url"], "cap": sorted(x["cap"]), "ky_nang": sorted(x["ky_nang"])}
        for x in EXTERNAL
    ]


@router.get("/{tai_lieu_id}/tep")
def material_file(
    tai_lieu_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _student: dict = Depends(require_student),
):
    """Học viên mở tệp tài liệu đang đăng (tệp lưu riêng, không công khai qua /media)."""
    row = run_service(lambda: published_material_file(db, tai_lieu_id), "Không tìm thấy tài liệu")
    try:
        path = resolve(row["duong_dan"])
    except ValueError:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp")
    return FileResponse(
        path,
        media_type=_MEDIA_TYPES[row["loai_tep"]],
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
