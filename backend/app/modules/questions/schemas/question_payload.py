import re
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TOP_TYPES = ("ngu_lieu", "chon_mot", "dung_sai", "sap_xep", "dien_chu", "viet_mo")
CHILD_TYPES = ("chon_mot", "dung_sai", "chon_bo_chung", "sap_xep", "dien_chu", "viet_mo")
SKILLS = ("nghe", "doc", "viet", "tu_vung")

# Đường dẫn tương đối trong thư mục uploads (vd audio/ab12.mp3); không cho "..", không đường dẫn tuyệt đối
_MEDIA_PATH = re.compile(r"^[A-Za-z0-9_\-]+(/[A-Za-z0-9_\-.]+)*\.[A-Za-z0-9]{2,5}$")


def _clean_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _clean_media(value):
    value = _clean_text(value)
    if value is None:
        return None
    if ".." in value or not _MEDIA_PATH.fullmatch(value):
        raise ValueError("Đường dẫn tệp không hợp lệ")
    return value


class _TextFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    noi_dung: str | None = Field(None, max_length=5000)
    tep_audio: str | None = Field(None, max_length=255)
    tep_hinh: str | None = Field(None, max_length=255)
    mo_ta_hinh: str | None = Field(None, max_length=1000)
    loi_nghe: str | None = Field(None, max_length=5000)
    pinyin: str | None = Field(None, max_length=5000)
    dich_nghia: str | None = Field(None, max_length=5000)
    goi_y: str | None = Field(None, max_length=2000)
    giai_thich: str | None = Field(None, max_length=5000)
    tu_bat_buoc: str | None = Field(None, max_length=20)
    tieu_chi_mo_ta: str | None = Field(None, max_length=5000)
    diem_toi_da: Decimal | None = Field(None, gt=0, max_digits=5, decimal_places=2)
    nguong_dat: Decimal | None = Field(None, gt=0, max_digits=5, decimal_places=2)
    dap_an_thu_tu: int | None = Field(None, ge=1, le=20)

    @field_validator("noi_dung", "mo_ta_hinh", "loi_nghe", "pinyin", "dich_nghia", "goi_y",
                     "giai_thich", "tu_bat_buoc", "tieu_chi_mo_ta", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)

    @field_validator("tep_audio", "tep_hinh", mode="before")
    @classmethod
    def _media(cls, value):
        return _clean_media(value)


class OptionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    noi_dung: str | None = Field(None, max_length=1000)
    tep_hinh: str | None = Field(None, max_length=255)
    la_dap_an_dung: bool = False

    @field_validator("noi_dung", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)

    @field_validator("tep_hinh", mode="before")
    @classmethod
    def _media(cls, value):
        return _clean_media(value)


class _AnswerFields(BaseModel):
    phuong_an: list[OptionIn] = Field(default_factory=list, max_length=12)
    dap_an_chap_nhan: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("dap_an_chap_nhan", mode="before")
    @classmethod
    def _accepted(cls, value):
        items = [_clean_text(v) for v in (value or [])]
        items = [v for v in items if v]
        if any(len(v) > 1000 for v in items):
            raise ValueError("Đáp án chấp nhận tối đa 1000 ký tự")
        return items


class ChildIn(_TextFields, _AnswerFields):
    id: int | None = Field(None, ge=1)  # id câu con của phiên bản đang sửa; bỏ trống = câu con mới
    dang: Literal[CHILD_TYPES]


class QuestionIn(_TextFields, _AnswerFields):
    dang: Literal[TOP_TYPES]
    cap_do_id: int = Field(..., ge=1)
    ky_nang: Literal[SKILLS]
    dung_on_luyen: bool = False
    dung_thi_thu: bool = True
    dung_dau_vao: bool = False
    tu_vung_id: int | None = Field(None, ge=1)  # Câu Từ vựng gắn một từ
    cau_con: list[ChildIn] = Field(default_factory=list, max_length=30)
