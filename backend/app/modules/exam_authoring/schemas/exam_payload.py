import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.questions.schemas.question_payload import _clean_media, _clean_text

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
