import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.security.require_lecturer import require_lecturer
from app.storage.static_media import UPLOADS_DIR

router = APIRouter()

# Loại tệp → (thư mục con, đuôi cho phép, dung lượng tối đa)
_KINDS = {
    "audio": ("audio", {"mp3", "m4a", "wav", "ogg"}, 20 * 1024 * 1024),
    "hinh": ("images", {"png", "jpg", "jpeg", "webp", "gif"}, 5 * 1024 * 1024),
}

# Dấu hiệu đầu tệp để không nhận tệp đổi đuôi
_SIGNATURES = {
    "png": [b"\x89PNG"], "jpg": [b"\xff\xd8\xff"], "jpeg": [b"\xff\xd8\xff"], "gif": [b"GIF8"],
    "webp": [b"RIFF"], "wav": [b"RIFF"], "ogg": [b"OggS"],
    "mp3": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"], "m4a": [],  # m4a: "ftyp" ở byte 4
}


def _looks_valid(ext: str, data: bytes) -> bool:
    if ext == "m4a":
        return data[4:8] == b"ftyp"
    return any(data.startswith(sig) for sig in _SIGNATURES[ext])


@router.post("/giang-vien/tep", status_code=status.HTTP_201_CREATED)
async def upload_media(
    request: Request,
    loai: Literal["audio", "hinh"] = Query(...),
    ten: str = Query(..., min_length=3, max_length=200),
    _lecturer: dict = Depends(require_lecturer),
):
    """Nhận nội dung tệp thô trong body (không cần multipart). Trả đường dẫn tương đối để lưu vào câu hỏi."""
    folder, allowed, max_size = _KINDS[loai]
    ext = ten.rsplit(".", 1)[-1].lower() if "." in ten else ""
    if ext not in allowed:
        raise HTTPException(status_code=422, detail=f"Chỉ nhận tệp: {', '.join(sorted(allowed))}")

    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_size:
        raise HTTPException(status_code=413, detail=f"Tệp vượt quá {max_size // (1024 * 1024)} MB")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > max_size:
            raise HTTPException(status_code=413, detail=f"Tệp vượt quá {max_size // (1024 * 1024)} MB")
    if not data:
        raise HTTPException(status_code=422, detail="Tệp rỗng")
    if not _looks_valid(ext, bytes(data[:16])):
        raise HTTPException(status_code=422, detail="Nội dung tệp không khớp đuôi tệp")

    name = f"{uuid.uuid4().hex}.{ext}"
    target_dir = UPLOADS_DIR / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / name).write_bytes(bytes(data))
    return {"duong_dan": f"{folder}/{name}"}
