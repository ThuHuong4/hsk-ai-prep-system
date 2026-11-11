from pydantic import BaseModel, ConfigDict, Field


class RequestPasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=3, max_length=255)