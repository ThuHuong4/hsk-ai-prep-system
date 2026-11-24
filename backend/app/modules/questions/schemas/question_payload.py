import re
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TOP_TYPES = ("ngu_lieu", "chon_mot", "dung_sai", "sap_xep", "dien_chu", "viet_mo", "dich_cau")
CHILD_TYPES = ("chon_mot", "dung_sai", "chon_bo_chung", "sap_xep", "dien_chu", "viet_mo", "dich_cau")
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
    goi_y_2: str | None = Field(None, max_length=2000)  # Gợi ý mức 2 (cách tiếp cận), chỉ mở sau gợi ý mức 1
    giai_thich: str | None = Field(None, max_length=5000)
    tu_bat_buoc: str | None = Field(None, max_length=20)
    tieu_chi_mo_ta: str | None = Field(None, max_length=5000)
    diem_toi_da: Decimal | None = Field(None, gt=0, max_digits=5, decimal_places=2)
    nguong_dat: Decimal | None = Field(None, gt=0, max_digits=5, decimal_places=2)
    dap_an_thu_tu: int | None = Field(None, ge=1, le=20)

    @field_validator("noi_dung", "mo_ta_hinh", "loi_nghe", "pinyin", "dich_nghia", "goi_y", "goi_y_2",
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
    # Nguồn nội dung; NULL = câu cũ chưa xác định nguồn (không tự gán)
    nguon_noi_dung: Literal["tu_soan", "soan_voi_ai", "nguon_duoc_phep"] | None = None
    nhom_kien_thuc_id: int | None = Field(None, ge=1)  # Nhóm kiến thức chính (dùng cho cá nhân hóa)
    cau_con: list[ChildIn] = Field(default_factory=list, max_length=30)


# Các dạng AI được phép soạn nháp (không gồm Ngữ liệu nhiều câu con)
AI_DRAFT_TYPES = ("chon_mot", "dung_sai", "sap_xep", "dien_chu", "viet_mo", "dich_cau")


class AiDraftIn(BaseModel):
    """Yêu cầu Giảng viên gửi để AI soạn bản nháp câu hỏi."""
    model_config = ConfigDict(extra="forbid")

    cap_do_id: int = Field(..., ge=1)
    ky_nang: Literal[SKILLS]
    dang: Literal[AI_DRAFT_TYPES]
    chu_de: str | None = Field(None, max_length=200)  # bỏ trống = để AI tự chọn chủ đề
    yeu_cau: str | None = Field(None, max_length=1000)
    so_luong: int = Field(5, ge=1, le=20)
    dung_thi_thu: bool = False  # bật khi soạn bù câu cho đề thi thử

    @field_validator("chu_de", "yeu_cau", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vai_tro: Literal["gv", "ai"]
    noi_dung: str = Field(..., min_length=1, max_length=6000)


class AiChatIn(BaseModel):
    """Giảng viên trao đổi với AI về một câu nháp; AI chỉ đề xuất bản sửa."""
    model_config = ConfigDict(extra="forbid")

    cau_hoi: QuestionIn
    tin_nhan: str = Field(..., min_length=1, max_length=1000)
    lich_su: list[ChatTurn] = Field(default_factory=list, max_length=20)

    @field_validator("tin_nhan", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value) or ""


class AiSuggestIn(BaseModel):
    """Giảng viên hỏi AI nên soạn gì; AI dựa vào số câu hiện có trong ngân hàng để gợi ý."""
    model_config = ConfigDict(extra="forbid")

    cap_do_id: int | None = Field(None, ge=1)
    ky_nang: Literal[SKILLS] | None = None
    tin_nhan: str | None = Field(None, max_length=1000)
    lich_su: list[ChatTurn] = Field(default_factory=list, max_length=20)

    @field_validator("tin_nhan", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)


class AssistantIn(BaseModel):
    """Giảng viên hỏi trợ lý AI (khung chat mở ở mọi trang)."""
    model_config = ConfigDict(extra="forbid")

    tin_nhan: str = Field(..., min_length=1, max_length=4000)
    lich_su: list[ChatTurn] = Field(default_factory=list, max_length=24)
    trang: str | None = Field(None, max_length=120)

    @field_validator("tin_nhan", "trang", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)


class AiBatchIn(BaseModel):
    """Danh sách câu gửi lên để AI soát lại hoặc để Giảng viên duyệt."""
    model_config = ConfigDict(extra="forbid")

    cau_hoi: list[QuestionIn] = Field(..., min_length=1, max_length=20)
