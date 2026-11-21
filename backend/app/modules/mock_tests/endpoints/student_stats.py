from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.mock_tests.services import stats_service
from app.security.require_student import require_student

router = APIRouter(prefix="/thi-thu")


# Mục 6.2: thống kê Thi thử của chính Học viên, tách theo cấp
@router.get("/thong-ke")
def my_stats(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return stats_service.student_stats(db, student["ma_nguoi_dung"])
