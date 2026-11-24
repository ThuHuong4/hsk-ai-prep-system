"""Tổng hợp phát âm tiếng Trung (MP3, có bộ nhớ đệm trên đĩa) cho từ điển Tra từ."""
import asyncio
import hashlib
from pathlib import Path
import re

import edge_tts
from fastapi import HTTPException

from app.integrations.ai.config import current_ai_config
from app.storage.static_media import UPLOADS_DIR

TTS_DICT_DIR = UPLOADS_DIR / "tts_dict"
MAX_TEXT_LEN = 80
_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")
_inflight: dict[str, asyncio.Lock] = {}


def clean_pronounce_text(raw: str) -> str:
    txt = _CTRL_RE.sub("", (raw or "").strip())
    if not txt or len(txt) > MAX_TEXT_LEN or not _CJK_RE.search(txt):
        raise HTTPException(status_code=400, detail="Văn bản phát âm phải là tiếng Trung hợp lệ (tối đa 80 ký tự).")
    return txt


async def get_or_create_mp3(raw_text: str) -> Path:
    txt = clean_pronounce_text(raw_text)
    voice = str(current_ai_config().get("edge_voice_nu") or "zh-CN-XiaoxiaoNeural")
    rate = "-10%"
    digest = hashlib.sha1(f"{voice}|{rate}|{txt}".encode("utf-8")).hexdigest()
    TTS_DICT_DIR.mkdir(parents=True, exist_ok=True)
    dest = TTS_DICT_DIR / f"{digest}.mp3"
    if dest.is_file() and dest.stat().st_size > 200:
        return dest

    lock = _inflight.setdefault(digest, asyncio.Lock())
    try:
        async with lock:
            if dest.is_file() and dest.stat().st_size > 200:
                return dest
            last_err: Exception | None = None
            for attempt in range(3):
                try:
                    comm = edge_tts.Communicate(txt, voice, rate=rate)
                    buf = bytearray()
                    async for chunk in comm.stream():
                        if chunk.get("type") == "audio" and chunk.get("data"):
                            buf.extend(chunk["data"])
                    if len(buf) <= 200:
                        raise RuntimeError("Dữ liệu âm thanh rỗng")
                    tmp = TTS_DICT_DIR / f"{digest}.{id(buf)}.tmp"
                    tmp.write_bytes(bytes(buf))
                    tmp.replace(dest)
                    return dest
                except Exception as exc:
                    last_err = exc
                    if attempt < 2:
                        await asyncio.sleep(0.5 * (attempt + 1))
            raise HTTPException(status_code=503, detail=f"Tạm thời chưa tạo được âm thanh phát âm: {last_err}")
    finally:
        _inflight.pop(digest, None)
