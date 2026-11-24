import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.questions.schemas.question_payload import ChatTurn, _clean_media, _clean_text

_CODE = re.compile(r"^[A-Za-z0-9_\-]{2,30}$")


class ExamInfoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cap_do_id: int = Field(..., ge=1)
    ten: str = Field(..., min_length=1, max_length=150)
    ma_de: str = Field(..., min_length=2, max_length=30)
    nguon: str | None = Field(None, max_length=255)
    thoi_luong_phut: int | None = Field(None, ge=1, le=300)
    tep_audio_chung: str | None = Field(None, max_length=255)

    @field_validator("ten", "nguon", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)

    @field_validator("ma_de", mode="before")
    @classmethod
    def _code(cls, value):
        value = (_clean_text(value) or "").upper()
        if not _CODE.fullmatch(value):
            raise ValueError("Mã đề 2–30 ký tự, chỉ gồm chữ không dấu, số, - và _")
        return value

    @field_validator("tep_audio_chung", mode="before")
    @classmethod
    def _media(cls, value):
        return _clean_media(value)


class ExamItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cau_hoi_id: int = Field(..., ge=1)
    phan: int | None = Field(None, ge=1, le=9)
    la_cau_vi_du: bool = False


class ExamItemsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cau_hoi: list[ExamItemIn] = Field(default_factory=list, max_length=200)


class ExamPartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ky_nang: Literal["nghe", "doc", "viet", "tu_vung"]
    so_cau: int = Field(..., ge=0, le=100)


class AiComposeIn(BaseModel):
    """Yêu cầu AI ghép đề (lần đầu) hoặc trao đổi để chỉnh lựa chọn hiện tại."""
    model_config = ConfigDict(extra="forbid")

    cap_do_id: int = Field(..., ge=1)
    cau_truc: list[ExamPartIn] = Field(..., min_length=1, max_length=4)
    yeu_cau: str | None = Field(None, max_length=1000)
    tin_nhan: str | None = Field(None, max_length=1000)
    lich_su: list[ChatTurn] = Field(default_factory=list, max_length=20)
    hien_tai: list[int] = Field(default_factory=list, max_length=200)

    @field_validator("yeu_cau", "tin_nhan", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)


class AiCreateExamIn(BaseModel):
    """Giảng viên đã xem danh sách câu AI chọn: tạo đề ở trạng thái nháp."""
    model_config = ConfigDict(extra="forbid")

    thong_tin: ExamInfoIn
    cau_hoi: list[ExamItemIn] = Field(..., min_length=1, max_length=200)


# ---------------------------------------------------------------- soạn đề mới với AI theo từng phần

class AiPartIn(BaseModel):
    """AI soạn một phần đề (hoặc soạn lại / soạn thêm một kiểu câu trong phần)."""
    model_config = ConfigDict(extra="forbid")

    cap_do_id: int = Field(..., ge=1)
    phan: int = Field(..., ge=1, le=9)
    kieu: str | None = Field(None, max_length=40)
    so_muc: int | None = Field(None, ge=1, le=20)
    chu_de: str | None = Field(None, max_length=200)
    yeu_cau: str | None = Field(None, max_length=1000)
    tranh: list[str] = Field(default_factory=list, max_length=40)  # nội dung đã có, để AI không lặp

    @field_validator("chu_de", "yeu_cau", "kieu", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)

    @field_validator("tranh", mode="before")
    @classmethod
    def _avoid(cls, value):
        return [str(v)[:200] for v in (value or []) if v][:40]


class AiPartChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cap_do_id: int = Field(..., ge=1)
    phan: int = Field(..., ge=1, le=9)
    muc: list[dict] = Field(..., min_length=1, max_length=25)
    tin_nhan: str = Field(..., min_length=1, max_length=1000)
    lich_su: list[ChatTurn] = Field(default_factory=list, max_length=20)

    @field_validator("tin_nhan", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value) or ""


class AiPartApproveIn(BaseModel):
    """Giảng viên xác nhận đã xem hình, nghe âm thanh và kiểm tra nội dung từng mục trước khi duyệt."""
    model_config = ConfigDict(extra="forbid")

    cap_do_id: int = Field(..., ge=1)
    phan: int = Field(..., ge=1, le=9)
    muc: list[dict] = Field(..., min_length=1, max_length=25)
    da_kiem_tra: Literal[True]


class AiImageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mo_ta: str = Field(..., min_length=3, max_length=800)


class AiAudioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cap_do_id: int = Field(..., ge=1)
    loi_nghe: str = Field(..., min_length=1, max_length=5000)


# ---------------------------------------------------------------- tạo đề hoàn chỉnh với AI (chạy nền)

class AiJobCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cap_do_id: int = Field(..., ge=1)
    chu_de: str | None = Field(None, max_length=200)
    yeu_cau: str | None = Field(None, max_length=1000)

    @field_validator("chu_de", "yeu_cau", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)


class AiJobFixIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tin_nhan: str = Field(..., min_length=1, max_length=1000)

    @field_validator("tin_nhan", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value) or ""


class AiJobMarkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dat: bool


class AiJobGreenIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phan: int | None = Field(None, ge=1, le=9)
    tat_ca_hop_le: bool = False


class AiJobFileIn(BaseModel):
    """Ô tệp: ["tep_hinh"], ["tep_audio"], ["lua_chon", i, "tep_hinh"], ["cau", i, "tep_audio"]."""
    model_config = ConfigDict(extra="forbid")

    path: list[str | int] = Field(..., min_length=1, max_length=3)
    duong_dan: str | None = Field(None, max_length=255)  # có = gắn tệp tự tải lên; trống = AI tạo lại

    @field_validator("duong_dan", mode="before")
    @classmethod
    def _media(cls, value):
        return _clean_media(value)


class AiJobPausesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nghi: dict[int, int] = Field(default_factory=dict)

    @field_validator("nghi")
    @classmethod
    def _range(cls, value):
        if any(not 1 <= k <= 9 or not 3 <= v <= 60 for k, v in value.items()):
            raise ValueError("Khoảng nghỉ mỗi câu từ 3 đến 60 giây")
        return value


class AiJobApproveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten: str = Field(..., min_length=1, max_length=150)
    ma_de: str = Field(..., min_length=2, max_length=30)
    thoi_luong_phut: int | None = Field(None, ge=1, le=300)

    @field_validator("ten", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)

    @field_validator("ma_de", mode="before")
    @classmethod
    def _code(cls, value):
        value = (_clean_text(value) or "").upper()
        if not _CODE.fullmatch(value):
            raise ValueError("Mã đề 2–30 ký tự, chỉ gồm chữ không dấu, số, - và _")
        return value
