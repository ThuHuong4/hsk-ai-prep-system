import re
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.admin.services import admin_service as svc
from app.modules.admin.services import lecturer_invite
from app.modules.common.service_errors import run_service
from app.security.require_admin import require_admin

router = APIRouter(prefix="/quan-tri")
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USER_404 = "Không tìm thấy tài khoản"


class _Reason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ly_do: str | None = Field(None, max_length=255)

    @field_validator("ly_do", mode="before")
    @classmethod
    def _strip(cls, value):
        return (value or "").strip() or None if isinstance(value, str) or value is None else value


class LockIn(_Reason):
    pass


class RoleIn(_Reason):
    vai_tro_id: Literal[1, 3]


class LecturerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ho_ten: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)

    @field_validator("ho_ten", mode="before")
    @classmethod
    def _clean_name(cls, value):
        if isinstance(value, str):
            value = " ".join(value.split())
            if any(ord(ch) < 32 for ch in value):
                raise ValueError("Họ tên chứa ký tự không hợp lệ")
        return value

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        value = value.strip()
        if not _EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Email không hợp lệ")
        return value


class RoleNameIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten: str = Field(..., min_length=2, max_length=50)

    @field_validator("ten", mode="before")
    @classmethod
    def _clean(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value


@router.get("/tong-quan")
def get_overview(db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    return svc.overview(db)


@router.get("/tai-khoan")
def get_accounts(q: str | None = Query(None, max_length=100), vai_tro: int | None = Query(None, ge=1, le=3),
                 trang_thai: Literal["hoat_dong", "khoa"] | None = Query(None), trang: int = Query(1, ge=1),
                 db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    return svc.list_accounts(db, (q or "").strip() or None, vai_tro, trang_thai, trang)


@router.post("/tai-khoan/{user_id}/khoa")
def lock_account(body: LockIn, user_id: int = Path(..., ge=1), db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    return {"message": run_service(lambda: svc.set_locked(db, admin["ma_nguoi_dung"], user_id, True, body.ly_do), _USER_404)}


@router.post("/tai-khoan/{user_id}/mo-khoa")
def unlock_account(body: LockIn, user_id: int = Path(..., ge=1), db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    return {"message": run_service(lambda: svc.set_locked(db, admin["ma_nguoi_dung"], user_id, False, body.ly_do), _USER_404)}


@router.post("/tai-khoan/{user_id}/vai-tro")
def change_role(body: RoleIn, user_id: int = Path(..., ge=1), db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    return {"message": run_service(lambda: svc.set_role(db, admin["ma_nguoi_dung"], user_id, body.vai_tro_id, body.ly_do), _USER_404)}


@router.get("/nhat-ky")
def get_logs(hanh_dong: Literal["khoa", "mo_khoa", "doi_vai_tro", "tao_tai_khoan"] | None = Query(None), q: str | None = Query(None, max_length=100),
             db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    return svc.recent_logs(db, hanh_dong, (q or "").strip() or None)


@router.get("/tai-khoan/{user_id}")
def get_account(user_id: int = Path(..., ge=1), db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    return run_service(lambda: svc.account_detail(db, user_id), _USER_404)


@router.post("/giang-vien", status_code=201)
def create_lecturer(body: LecturerIn, db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    return run_service(lambda: lecturer_invite.create_lecturer(db, admin["ma_nguoi_dung"], body.ho_ten, body.email))


@router.post("/tai-khoan/{user_id}/gui-lai-email")
def resend_invite(user_id: int = Path(..., ge=1), db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    return run_service(lambda: lecturer_invite.resend_invite(db, admin["ma_nguoi_dung"], user_id), _USER_404)


@router.get("/vai-tro")
def get_roles(db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    return svc.list_roles(db)


@router.put("/vai-tro/{role_id}")
def put_role(body: RoleNameIn, role_id: int = Path(..., ge=1), db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    return {"message": run_service(lambda: svc.rename_role(db, role_id, body.ten), "Không tìm thấy vai trò")}
