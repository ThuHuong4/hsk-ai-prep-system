from pydantic import BaseModel, ConfigDict, Field


class SaveAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cau_tra_loi: str | None = Field(..., max_length=10)
    danh_dau_xem_lai: bool
    so_thu_tu_luu: int = Field(..., ge=1, le=4_294_967_295)