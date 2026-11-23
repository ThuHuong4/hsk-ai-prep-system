from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import run_service
from app.modules.mock_tests.services import roadmap_service
from app.security.require_student import require_student

router = APIRouter()


# Mục 6.2: lần đầu gọi thì tạo gợi ý (AI một lần) rồi lưu; các lần sau trả bản đã lưu
@router.post("/thi-thu/luot/{luot_id}/goi-y-lo-trinh")
def roadmap(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(
        lambda: roadmap_service.get_roadmap(db, luot_id, student["ma_nguoi_dung"]),
        "Không tìm thấy lượt làm bài",
    )
