from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import run_service
from app.modules.mock_tests.services import roadmap_service
from app.security.require_student import require_student
from app.storage.private_files import resolve

router = APIRouter()
_MEDIA_TYPES = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "mp3": "audio/mpeg", "wav": "audio/wav"}


# Mục 6.2: lần đầu gọi thì tạo gợi ý (AI một lần) rồi lưu; các lần sau trả bản đã lưu
@router.post("/thi-thu/luot/{luot_id}/goi-y-lo-trinh")
def roadmap(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: roadmap_service.get_roadmap(db, luot_id, student["ma_nguoi_dung"]), "Không tìm thấy lượt làm bài")


# Học viên mở tài liệu đang đăng (tệp lưu riêng, cần đăng nhập)
@router.get("/tai-lieu/{tai_lieu_id}/tep")
def material_file(tai_lieu_id: int = Path(..., ge=1), db: Session = Depends(get_db), _student: dict = Depends(require_student)):
    row = run_service(lambda: roadmap_service.material_file(db, tai_lieu_id), "Không tìm thấy tài liệu")
    try:
        path = resolve(row["duong_dan"])
    except ValueError:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp")
    return FileResponse(path, media_type=_MEDIA_TYPES[row["loai_tep"]],
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
