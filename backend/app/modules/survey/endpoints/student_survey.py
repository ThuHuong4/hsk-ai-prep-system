from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import run_service
from app.modules.survey.services import survey_service
from app.security.require_student import require_student

router = APIRouter(prefix="/khao-sat")


class SurveyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    da_hoc: Literal["chua", "da_hoc"]
    cap_muc_tieu_id: int = Field(..., ge=1)
    muc_dich: Literal["on_luyen", "thi_thu", "ca_hai"]
    ky_nang: Literal["nghe", "doc", "viet", "tu_vung"]
    phut_moi_ngay: Literal[10, 15, 30, 60]


@router.get("")
def get_survey(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return survey_service.get_survey(db, student["ma_nguoi_dung"])


@router.post("")
def post_survey(body: SurveyIn, db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: survey_service.submit_survey(db, student["ma_nguoi_dung"], body))


@router.post("/bo-qua", status_code=status.HTTP_204_NO_CONTENT)
def skip_survey(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    survey_service.skip_survey(db, student["ma_nguoi_dung"])
