"""Các Pydantic schema dùng chung cho kiểm tra câu trả lời và tin nhắn Hỏi Xiang giữa nhiều module."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CheckAnswerIn(BaseModel):
    """Dữ liệu gửi lên khi bấm Kiểm tra hoặc Bỏ qua một câu hỏi (cả hai trường đáp án trống = Bỏ qua)."""
    model_config = ConfigDict(extra="forbid")

    cau_hoi_id: int = Field(..., ge=1)
    phuong_an_chon_id: int | None = Field(None, ge=1)
    van_ban: str | None = Field(None, max_length=2000)


class ChatTurnIn(BaseModel):
    """Một lượt tin nhắn trong khung Hỏi Xiang."""
    model_config = ConfigDict(extra="forbid")

    vai: Literal["hoc_vien", "xiang"]
    noi_dung: str = Field(..., min_length=1, max_length=2000)
