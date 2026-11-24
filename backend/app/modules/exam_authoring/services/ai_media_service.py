"""Tạo tệp âm thanh và hình cho câu đề do AI soạn; lưu vào thư mục uploads như tệp Giảng viên tải lên.

Âm thanh: lời nghe ghi theo dòng "男：", "女：", "问：" -> mỗi dòng một giọng, chèn khoảng lặng,
cấp HSK 1–3 phát lại 2 lần trong cùng tệp như băng đề thật. Tệp WAV (không cần ffmpeg).
Hình: ảnh chụp đơn giản, cấm chữ/số trong hình (AI vẽ chữ Hán hay sai).
"""
import io
import json
import re
import threading
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor

from app.integrations.ai import (
    PCM_RATE,
    AiNotConfiguredError,
    AiProviderError,
    ai_ready,
    chat_completion,
    image_bytes,
    image_ready,
    parse_json_reply,
    speech_pcm,
    tts_ready,
)
from app.storage.static_media import UPLOADS_DIR

_SPEAKER = re.compile(r"^\s*(男|女|问|問)\s*[：:]\s*")
_GAP_LINE = 0.6     # giây lặng giữa hai lượt lời
_GAP_QUESTION = 1.2  # trước câu hỏi
_GAP_REPEAT = 2.5    # giữa lần phát 1 và lần phát 2
MAX_LINES = 40


class AiMediaError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _silence(seconds: float) -> bytes:
    return b"\x00\x00" * int(PCM_RATE * seconds)


def split_lines(script: str) -> list[tuple[str, str]]:
    """Tách lời nghe thành [(giọng, câu)]; dòng không ghi người nói đọc bằng giọng nữ."""
    lines = []
    for raw in (script or "").splitlines():
        if not raw.strip():
            continue
        found = _SPEAKER.match(raw)
        role = {"男": "nam", "女": "nu"}.get(found.group(1), "hoi") if found else "nu"
        content = raw[found.end():].strip() if found else raw.strip()
        if content:
            lines.append((role, content))
    return lines


def _voice(role: str) -> str:
    return role if role in ("nam", "nu") else "hoi"


def _save(folder: str, ext: str, data: bytes) -> str:
    name = f"{uuid.uuid4().hex}.{ext}"
    target = UPLOADS_DIR / folder
    target.mkdir(parents=True, exist_ok=True)
    (target / name).write_bytes(data)
    return f"{folder}/{name}"


def make_audio(script: str, plays: int = 1, slow: bool = False) -> str:
    """Đọc lời nghe nhiều giọng thành một tệp WAV; trả đường dẫn tương đối trong uploads."""
    lines = split_lines(script)
    if not lines:
        raise AiMediaError("Lời nghe trống", 422)
    if len(lines) > MAX_LINES:
        raise AiMediaError(f"Lời nghe tối đa {MAX_LINES} dòng", 422)
    if not tts_ready():
        raise AiMediaError("Bộ tạo giọng đọc AI chưa sẵn sàng (cài gói edge-tts và miniaudio)", 503)
    try:
        with ThreadPoolExecutor(max_workers=min(3, len(lines))) as pool:
            chunks = list(pool.map(lambda line: speech_pcm(line[1], _voice(line[0]), slow), lines))
    except AiNotConfiguredError as error:
        raise AiMediaError(str(error) or "Chưa cấu hình giọng đọc AI", 503) from error
    except AiProviderError as error:
        raise AiMediaError(str(error) or "Dịch vụ giọng đọc đang bận, vui lòng thử lại", 502) from error

    once = bytearray()
    for index, ((role, _), pcm) in enumerate(zip(lines, chunks)):
        if index:
            once += _silence(_GAP_QUESTION if role == "hoi" else _GAP_LINE)
        once += pcm
    body = bytearray(_silence(0.5))
    for turn in range(max(1, plays)):
        if turn:
            body += _silence(_GAP_REPEAT)
        body += once
    body += _silence(0.5)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(PCM_RATE)
        wav.writeframes(bytes(body))
    return _save("audio", "wav", buffer.getvalue())


_IMAGE_STYLE = (
    "A clear, realistic photograph used as a picture in a Chinese proficiency exam (HSK). "
    "Show this exact everyday scene: {desc}. Single clear subject and action, natural daylight, clean uncluttered background. "
    "Strictly NO text, NO letters, NO Chinese characters, NO numbers, NO signs, NO logos, NO watermarks."
)
_TRANSLATE_IMG_SYSTEM = (
    "Convert the given Vietnamese/Chinese HSK exam picture description into JSON: "
    '{"scene": "one clear English visual sentence under 25 words", "keywords": "3 to 4 simple English photo search nouns/verbs"}. '
    "Return valid JSON only."
)
_BATCH_TRANSLATE_SYSTEM = (
    "Convert each numbered Vietnamese/Chinese HSK exam picture description into concise English visual description and 3-4 simple photo search keywords. "
    'Return valid JSON: {"items": [{"i": 0, "scene": "A woman eating a slice of watermelon", "keywords": "woman eating watermelon"}]}'
)
_SCENE_CACHE: dict[str, tuple[str, str]] = {}
_SCENE_LOCK = threading.Lock()


def translate_scenes_batch(descriptions: list[str]) -> None:
    """Dịch gộp toàn bộ mô tả hình của cả đề chỉ trong 1–2 lượt gọi AI (không tốn 37 lượt lẻ làm chạm trần gói miễn phí)."""
    unique = []
    with _SCENE_LOCK:
        for raw in descriptions:
            d = " ".join((raw or "").split())[:800]
            if len(d) >= 2 and d not in _SCENE_CACHE and d not in unique and any(ord(ch) > 127 for ch in d):
                unique.append(d)
    if not unique or not ai_ready():
        return
    for start in range(0, len(unique), 25):
        chunk = unique[start:start + 25]
        payload = [{"i": idx, "mo_ta": text} for idx, text in enumerate(chunk)]
        try:
            raw = chat_completion(_BATCH_TRANSLATE_SYSTEM, [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
            parsed = parse_json_reply(raw)
            rows = parsed.get("items") if isinstance(parsed, dict) else parsed
            if isinstance(rows, list):
                with _SCENE_LOCK:
                    for r in rows:
                        if isinstance(r, dict) and isinstance(r.get("i"), int) and 0 <= r["i"] < len(chunk):
                            scene = " ".join(str(r.get("scene") or "").split())[:280]
                            kw = " ".join(str(r.get("keywords") or "").split())[:100]
                            if scene:
                                _SCENE_CACHE[chunk[r["i"]]] = (scene, kw or scene)
        except Exception:
            continue


def _to_english_scene(desc: str) -> tuple[str, str]:
    with _SCENE_LOCK:
        if desc in _SCENE_CACHE:
            return _SCENE_CACHE[desc]
    if not any(ord(ch) > 127 for ch in desc) or not ai_ready():
        return desc, desc
    try:
        raw = chat_completion(_TRANSLATE_IMG_SYSTEM, [{"role": "user", "content": desc}])
        parsed = parse_json_reply(raw)
        if isinstance(parsed, dict) and parsed.get("scene"):
            scene = " ".join(str(parsed["scene"]).split())[:280]
            kw = " ".join(str(parsed.get("keywords") or scene).split())[:100]
            with _SCENE_LOCK:
                _SCENE_CACHE[desc] = (scene, kw)
            return scene, kw
    except Exception:
        pass
    return desc, desc


def make_image(description: str) -> str:
    desc = " ".join((description or "").split())[:800]
    if len(desc) < 2:
        raise AiMediaError("Mô tả hình quá ngắn", 422)
    if not image_ready():
        raise AiMediaError("Bộ tạo hình AI chưa sẵn sàng", 503)
    scene_en, keywords = _to_english_scene(desc)
    try:
        data, ext = image_bytes(_IMAGE_STYLE.format(desc=scene_en), keywords=keywords)
    except AiNotConfiguredError as error:
        raise AiMediaError(str(error) or "Chưa cấu hình tạo hình AI", 503) from error
    except AiProviderError as error:
        raise AiMediaError(str(error) or "Dịch vụ tạo hình đang bận, vui lòng thử lại", 502) from error
    return _save("images", ext, data)
