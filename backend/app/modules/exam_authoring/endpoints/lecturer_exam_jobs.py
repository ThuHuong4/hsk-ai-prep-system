"""Tạo đề hoàn chỉnh với AI (chạy nền) và màn Giảng viên duyệt đề."""
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.exam_authoring.schemas.exam_payload import (
    AiJobApproveIn,
    AiJobCreateIn,
    AiJobFileIn,
    AiJobFixIn,
    AiJobGreenIn,
    AiJobMarkIn,
    AiJobPausesIn,
)
from app.modules.exam_authoring.services import exam_job_service as svc
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien/de-thi/ai-de")
_JOB = Path(..., pattern=r"^[0-9a-f]{32}$")
_KEY = Path(..., pattern=r"^[0-9a-f]{12}$")


def _run(action):
    try:
        return action()
    except svc.JobError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)


def _me(lecturer: dict) -> int:
    return lecturer["ma_nguoi_dung"]


@router.get("")
def get_jobs(lecturer: dict = Depends(require_lecturer)):
    return {"phien": svc.list_jobs(_me(lecturer)), "san_sang": svc.readiness()}


@router.post("", status_code=status.HTTP_201_CREATED)
def post_job(body: AiJobCreateIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    """Bắt đầu soạn đề hoàn chỉnh; chạy nền, Giảng viên có thể rời trang."""
    job_id = _run(lambda: svc.create_job(db, body.cap_do_id, body.chu_de, body.yeu_cau, _me(lecturer)))
    return {"id": job_id}


@router.get("/{job_id}")
def get_job(job_id: str = _JOB, lecturer: dict = Depends(require_lecturer)):
    return _run(lambda: svc.get_job(job_id, _me(lecturer)))


@router.post("/{job_id}/chay-tiep")
def post_resume(job_id: str = _JOB, lecturer: dict = Depends(require_lecturer)):
    _run(lambda: svc.resume(job_id, _me(lecturer)))
    return {"message": "Đã chạy tiếp"}


@router.delete("/{job_id}")
def delete_job(job_id: str = _JOB, lecturer: dict = Depends(require_lecturer)):
    _run(lambda: svc.delete_job(job_id, _me(lecturer)))
    return {"message": "Đã bỏ phiên soạn đề"}


@router.post("/{job_id}/muc/{key}/dat")
def post_mark(body: AiJobMarkIn, job_id: str = _JOB, key: str = _KEY, lecturer: dict = Depends(require_lecturer)):
    return _run(lambda: svc.mark(job_id, _me(lecturer), key, body.dat))


@router.post("/{job_id}/dat-xanh")
def post_mark_green(body: AiJobGreenIn, job_id: str = _JOB, lecturer: dict = Depends(require_lecturer)):
    return _run(lambda: svc.mark_green(job_id, _me(lecturer), body.phan, body.tat_ca_hop_le))


@router.post("/{job_id}/muc/{key}/sua")
def post_fix(body: AiJobFixIn, job_id: str = _JOB, key: str = _KEY, db: Session = Depends(get_db),
             lecturer: dict = Depends(require_lecturer)):
    """Nhờ AI sửa một mục theo lời Giảng viên; kiểm định lại và tạo lại tệp đổi nội dung."""
    return _run(lambda: svc.ask_fix(db, job_id, _me(lecturer), key, body.tin_nhan))


@router.post("/{job_id}/muc/{key}/lam-lai")
def post_redo(job_id: str = _JOB, key: str = _KEY, db: Session = Depends(get_db),
              lecturer: dict = Depends(require_lecturer)):
    return _run(lambda: svc.redo(db, job_id, _me(lecturer), key))


@router.post("/{job_id}/muc/{key}/tep")
def post_file(body: AiJobFileIn, job_id: str = _JOB, key: str = _KEY, lecturer: dict = Depends(require_lecturer)):
    """Tạo lại một tệp bằng AI, hoặc gắn tệp Giảng viên tự tải lên."""
    if body.duong_dan:
        return _run(lambda: svc.attach_file(job_id, _me(lecturer), key, body.path, body.duong_dan))
    return _run(lambda: svc.remake_file(job_id, _me(lecturer), key, body.path))


@router.post("/{job_id}/ghep-am-thanh")
def post_assemble(body: AiJobPausesIn, job_id: str = _JOB, lecturer: dict = Depends(require_lecturer)):
    return _run(lambda: svc.reassemble(job_id, _me(lecturer), body.nghi))


@router.post("/{job_id}/duyet")
def post_approve(body: AiJobApproveIn, job_id: str = _JOB, db: Session = Depends(get_db),
                 lecturer: dict = Depends(require_lecturer)):
    """Giảng viên duyệt: lưu + đăng câu (ghi người duyệt), tạo đề kèm bài Nghe chung, đăng đề."""
    return _run(lambda: svc.approve(db, job_id, _me(lecturer), body.ten, body.ma_de, body.thoi_luong_phut))
