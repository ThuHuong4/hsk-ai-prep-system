"""Học viên xem Tài liệu ôn tập (mục 6.5): chỉ tài liệu đang đăng, cần đăng nhập.

Danh sách trả thông tin mô tả, không trả đường dẫn tệp; mở tệp qua GET /tai-lieu/{id}/tep (đã kiểm tra quyền và trạng thái).
Xem tài liệu không hoàn thành bài, không cộng KN, không tính nhiệm vụ.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.mock_tests.services.roadmap_service import EXTERNAL
from app.security.require_student import require_student

router = APIRouter(prefix="/tai-lieu")


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


# Nguồn học bên ngoài có tên đơn vị cụ thể (dùng chung danh sách với Gợi ý lộ trình): chỉ dẫn link, không lưu/tải lại nội dung
@router.get("/lien-ket")
def external_links(_student: dict = Depends(require_student)):
    return [{"ten": x["ten"], "mo_ta": x["mo_ta"], "url": x["url"], "cap": sorted(x["cap"]), "ky_nang": sorted(x["ky_nang"])}
            for x in EXTERNAL]
