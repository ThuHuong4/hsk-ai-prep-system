from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.attempts.endpoints.save_answer_request import SaveAnswerRequest
from app.modules.attempts.services.save_answer import (
    AttemptExpiredError,
    AttemptFinishedError,
    AttemptNotFoundError,
    InvalidAnswerError,
    QuestionNotInAttemptError,
    SaveConflictError,
    save_answer,
)
from app.security.current_user import get_current_user

router = APIRouter()


@router.put("/attempts/{ma_luot}/answers/{ma_cau_hoi}")
def put_answer(
    body: SaveAnswerRequest,
    ma_luot: int = Path(..., ge=1),
    ma_cau_hoi: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        return save_answer(
            db,
            current_user["ma_nguoi_dung"],
            ma_luot,
            ma_cau_hoi,
            body.cau_tra_loi,
            body.danh_dau_xem_lai,
            body.so_thu_tu_luu,
        )
    except AttemptNotFoundError:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt thi")
    except QuestionNotInAttemptError:
        raise HTTPException(status_code=404, detail="Câu hỏi không thuộc lượt thi")
    except AttemptFinishedError:
        raise HTTPException(status_code=409, detail="Lượt thi đã kết thúc")
    except AttemptExpiredError:
        # Tạm thời: bước nộp bài sẽ tự chấm lượt quá hạn
        raise HTTPException(status_code=409, detail="Lượt thi đã hết giờ")
    except InvalidAnswerError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except SaveConflictError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "ma_loi": "XUNG_DOT_PHIEN_BAN",
                "thong_bao": "Câu trả lời đã được lưu với nội dung khác",
                "hien_tai": error.current,
            },
        )