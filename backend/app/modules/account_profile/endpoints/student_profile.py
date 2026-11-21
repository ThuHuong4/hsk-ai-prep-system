from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.account_profile.services import profile_service as svc
from app.modules.common.service_errors import run_service
from app.security.require_student import require_student

router = APIRouter(prefix="/ca-nhan")


class NameIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ho_ten: str = Field(..., min_length=1, max_length=100)

    @field_validator("ho_ten")
    @classmethod
    def _check(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Họ tên không được để trống")
        if any(ord(ch) < 32 for ch in value):
            raise ValueError("Họ tên có ký tự không hợp lệ")
        return value


class ReminderIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nhan_email_nhac: bool


class PasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mat_khau_cu: str = Field(..., min_length=1, max_length=128)
    mat_khau_moi: str = Field(..., min_length=1, max_length=128)


@router.get("")
def get_profile(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return svc.get_profile(db, student["ma_nguoi_dung"])


@router.patch("/ho-so")
def update_name(body: NameIn, db: Session = Depends(get_db), student: dict = Depends(require_student)):
    run_service(lambda: svc.update_name(db, student["ma_nguoi_dung"], body.ho_ten))
    return {"ho_ten": body.ho_ten}


@router.patch("/nhac-hoc")
def update_reminder(body: ReminderIn, db: Session = Depends(get_db), student: dict = Depends(require_student)):
    run_service(lambda: svc.update_reminder(db, student["ma_nguoi_dung"], body.nhan_email_nhac))
    return {"nhan_email_nhac": body.nhan_email_nhac}


@router.post("/doi-mat-khau")
def change_password(body: PasswordIn, db: Session = Depends(get_db), student: dict = Depends(require_student)):
    try:
        run_service(lambda: svc.change_password(db, student["ma_nguoi_dung"], body.mat_khau_cu, body.mat_khau_moi))
    except svc.TooManyAttemptsError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Nhập sai mật khẩu hiện tại quá nhiều lần, thử lại sau 15 phút")
    return {"message": "Đã đổi mật khẩu"}
