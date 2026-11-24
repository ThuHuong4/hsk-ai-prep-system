"""Khóa các đường dẫn học thử công khai cũ: bắt buộc Đăng nhập -> Đánh giá trình độ đầu vào 8 câu trước khi Ôn luyện."""
from fastapi import APIRouter, HTTPException, Path, status

router = APIRouter(prefix="/cong-khai")
_LOGIN_REQUIRED = "Vui lòng đăng nhập và hoàn thành Đánh giá trình độ đầu vào 8 câu để ôn luyện đúng trình độ."


@router.get("/on-luyen/tong-quan", include_in_schema=False)
def blocked_guest_overview():
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_LOGIN_REQUIRED)


@router.get("/on-luyen/lo-trinh", include_in_schema=False)
def blocked_guest_path():
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_LOGIN_REQUIRED)


@router.get("/on-luyen/bai/{ma_goc_id}", include_in_schema=False)
def blocked_guest_lesson(ma_goc_id: int = Path(..., ge=1)):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_LOGIN_REQUIRED)


@router.post("/on-luyen/bai/{ma_goc_id}/kiem-tra", include_in_schema=False)
def blocked_guest_check(ma_goc_id: int = Path(..., ge=1)):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_LOGIN_REQUIRED)


@router.post("/hoi-xiang", include_in_schema=False)
def blocked_guest_ask():
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_LOGIN_REQUIRED)
