"""Gọi AI tạo giọng đọc tiếng Trung, tạo hình minh họa, nhìn ảnh và nghe lại (hỗ trợ mặc định miễn phí 100%).

- Giọng đọc tiếng Trung (TTS): Mặc định dùng `edge-tts` + `miniaudio` (miễn phí, không cần API key, trả PCM 24 kHz 16-bit mono).
- Tạo hình minh họa: Mặc định dùng Pollinations Flux miễn phí (không cần API key); tự ưu tiên HuggingFace `FLUX.1-schnell` nếu có `HF_API_KEY`.
- Nhìn ảnh & Nghe lại: Tự tương thích Google Gemini miễn phí, Groq miễn phí và OpenAI.
- Không giữ giao dịch CSDL khi gọi các hàm này. Không ghi khóa API vào log.
"""
import asyncio
import base64
import random
import re
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests
from openai import OpenAIError

from app.integrations.ai.client import AiNotConfiguredError, AiProviderError, get_ai_client
from app.integrations.ai.config import (
    MEDIA_TIMEOUT_SECONDS,
    current_ai_config,
    edge_tts_available,
    image_ready,
    is_real_openai_endpoint,
    resolve_stt_mode,
    resolve_vision_model,
    stt_ready,
    tts_ready,
    vision_ready,
)

PCM_RATE = 24000  # Chuẩn PCM 24 kHz, 16-bit signed, mono để ghép băng nghe WAV/MP3
_IMG_SEMAPHORE = threading.BoundedSemaphore(1)
_POLLINATIONS_COOLDOWN_UNTIL = 0.0
_WIKI_LOCK = threading.Lock()
_RECENT_WIKI_URLS: list[str] = []
_BLANK_RE = re.compile(r"_{2,}|（\s*）|\(\s*\)")
_STOP_WORDS = {
    "a", "an", "the", "of", "in", "on", "at", "with", "and", "or", "to", "for", "from", "by",
    "clear", "realistic", "photograph", "photo", "picture", "used", "chinese", "proficiency",
    "exam", "hsk", "show", "exactly", "this", "scene", "single", "subject", "action", "natural",
    "daylight", "clean", "uncluttered", "background", "strictly", "no", "text", "letters",
    "characters", "numbers", "signs", "logos", "watermarks", "young", "person",
}
_BAD_TITLE_TOKENS = ("map", "diagram", "chart", "graph", "logo", "icon", "flag", "stamp", "document", "page", "scan", "poster", "sign", "coat_of_arms")


def _detect_image_ext(data: bytes) -> str | None:
    if not data or len(data) < 1024:
        return None
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    return None


def _resolve_edge_voice(voice: str, cfg: dict) -> str:
    v = (voice or "").strip()
    if "Neural" in v:
        return v
    low = v.lower()
    if low in ("nam", "onyx", "echo", "fable", "ash", "male"):
        return cfg["edge_voice_nam"]
    if low in ("nu", "nova", "shimmer", "coral", "female"):
        return cfg["edge_voice_nu"]
    return cfg["edge_voice_hoi"]


def _run_coro_sync(coro):
    """Chạy coroutine an toàn dù gọi từ luồng đồng bộ hay luồng đang có sẵn event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _edge_speech_pcm(text: str, voice: str, slow: bool, cfg: dict) -> bytes:
    if not edge_tts_available():
        raise AiNotConfiguredError("Chưa cài đặt gói edge-tts và miniaudio")
    import edge_tts
    import miniaudio

    cleaned = _BLANK_RE.sub("，", (text or "").strip())
    if not cleaned:
        raise AiProviderError("Nội dung cần đọc đang trống")
    edge_voice = _resolve_edge_voice(voice, cfg)
    rate = "-16%" if slow else "-4%"

    async def _synthesize() -> bytes:
        comm = edge_tts.Communicate(cleaned, edge_voice, rate=rate)
        audio_mp3 = bytearray()
        async for chunk in comm.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                audio_mp3.extend(chunk["data"])
        return bytes(audio_mp3)

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            mp3_bytes = _run_coro_sync(_synthesize())
            if mp3_bytes:
                decoded = miniaudio.decode(
                    mp3_bytes,
                    output_format=miniaudio.SampleFormat.SIGNED16,
                    nchannels=1,
                    sample_rate=PCM_RATE,
                )
                pcm = decoded.samples.tobytes()
                if pcm:
                    return pcm
            last_err = AiProviderError("Dịch vụ giọng đọc trả về rỗng")
        except Exception as err:
            last_err = err
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
    raise AiProviderError("Không tạo được giọng đọc tiếng Trung, vui lòng kiểm tra mạng và thử lại") from last_err


def _openai_speech_pcm(text: str, voice: str, slow: bool, cfg: dict) -> bytes:
    model = cfg["tts_model"] or "gpt-4o-mini-tts"
    oa_voice = voice if voice in ("alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer") else (
        "onyx" if voice == "nam" else ("nova" if voice == "nu" else "alloy")
    )
    client = get_ai_client().with_options(timeout=MEDIA_TIMEOUT_SECONDS)
    kwargs = {"model": model, "voice": oa_voice, "input": text, "response_format": "pcm"}
    if model.startswith("gpt-"):
        kwargs["instructions"] = (
            "Speak in clear standard Mandarin Chinese like an official HSK listening recording, "
            + ("at a slow pace." if slow else "at a moderate pace.")
        )
    elif slow:
        kwargs["speed"] = 0.85
    response = client.audio.speech.create(**kwargs)
    data = response.read()
    if not data:
        raise AiProviderError("Dịch vụ giọng đọc trả về rỗng")
    return data


def speech_pcm(text: str, voice: str, slow: bool = False) -> bytes:
    """Đọc một câu tiếng Trung, trả PCM thô 24 kHz 16-bit mono (để ghép nhiều giọng và chèn khoảng lặng)."""
    if not tts_ready():
        raise AiNotConfiguredError("Chưa sẵn sàng bộ tạo giọng đọc AI")
    cfg = current_ai_config()
    want_openai = (
        cfg["tts_provider"] == "openai"
        or (
            cfg["tts_provider"] not in ("edge", "free")
            and bool(cfg["api_key"] and cfg["tts_model"])
            and cfg["tts_model"] not in ("edge-tts", "free")
            and is_real_openai_endpoint(cfg["base_url"])
        )
    )
    if want_openai:
        try:
            return _openai_speech_pcm(text, voice, slow, cfg)
        except Exception:
            if not edge_tts_available():
                raise AiProviderError("Không tạo được giọng đọc từ OpenAI")
    return _edge_speech_pcm(text, voice, slow, cfg)


def _hf_image_bytes(prompt: str, hf_key: str) -> tuple[bytes, str]:
    resp = requests.post(
        "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
        headers={"Authorization": f"Bearer {hf_key}", "Accept": "image/jpeg"},
        json={"inputs": prompt[:900]},
        timeout=45,
    )
    if resp.status_code != 200:
        raise AiProviderError(f"HuggingFace trả mã {resp.status_code}")
    ext = _detect_image_ext(resp.content)
    if not ext:
        raise AiProviderError("Dữ liệu ảnh HuggingFace không hợp lệ")
    return resp.content, ext


def _extract_search_queries(prompt: str, keywords: str = "") -> list[str]:
    queries: list[str] = []
    if keywords:
        kw = " ".join(re.findall(r"[A-Za-z]{2,}", keywords.lower()))
        if kw:
            words = kw.split()
            queries.append(" ".join(words[:5]))
            if len(words) > 3:
                queries.append(" ".join(words[:3]))
            if len(words) > 2:
                queries.append(" ".join(words[:2]))
    tokens = [w for w in re.findall(r"[A-Za-z]{3,}", (prompt or "").lower()) if w not in _STOP_WORDS]
    if tokens:
        queries.append(" ".join(tokens[:4]))
        if len(tokens) > 2:
            queries.append(" ".join(tokens[:2]))
    return list(dict.fromkeys(q for q in queries if q))


def _wikimedia_image_bytes(prompt: str, keywords: str = "") -> tuple[bytes, str]:
    """Tải ảnh chụp đời thực miễn phí từ kho Wikimedia Commons (không giới hạn lượt, tốc độ < 0.5 giây/ảnh)."""
    headers = {"User-Agent": "XianglingoHSK/1.0 (educational HSK exam builder; mailto:admin@xianglingo.local)"}
    queries = _extract_search_queries(prompt, keywords) or ["everyday life object"]
    for q in queries:
        try:
            resp = requests.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrnamespace": 6,
                    "gsrsearch": f"filetype:bitmap {q}",
                    "gsrlimit": 12,
                    "prop": "imageinfo",
                    "iiprop": "url|mime",
                    "iiurlwidth": 640,
                    "format": "json",
                },
                headers=headers,
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            pages = list(((resp.json().get("query") or {}).get("pages") or {}).values())
            random.shuffle(pages)
            for page in pages:
                title = (page.get("title") or "").lower().replace(" ", "_")
                if any(bad in title for bad in _BAD_TITLE_TOKENS):
                    continue
                info = (page.get("imageinfo") or [{}])[0]
                mime = info.get("mime") or ""
                url = info.get("thumburl") or info.get("url")
                if not url or mime not in ("image/jpeg", "image/png", "image/webp"):
                    continue
                with _WIKI_LOCK:
                    if url in _RECENT_WIKI_URLS:
                        continue
                img_resp = requests.get(url, headers=headers, timeout=18)
                if img_resp.status_code == 200:
                    ext = _detect_image_ext(img_resp.content)
                    if ext:
                        with _WIKI_LOCK:
                            _RECENT_WIKI_URLS.append(url)
                            if len(_RECENT_WIKI_URLS) > 120:
                                del _RECENT_WIKI_URLS[:40]
                        return img_resp.content, ext
        except Exception:
            continue
    raise AiProviderError("Không tìm được ảnh minh họa phù hợp")


def _pollinations_image_bytes(prompt: str) -> tuple[bytes, str]:
    global _POLLINATIONS_COOLDOWN_UNTIL
    if time.monotonic() < _POLLINATIONS_COOLDOWN_UNTIL:
        raise AiProviderError("Pollinations đang tạm giới hạn tốc độ IP")
    short_prompt = " ".join((prompt or "").split())[:550]
    encoded = urllib.parse.quote(short_prompt, safe="")
    seed = random.randint(1000, 999999)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=640&height=480&nologo=true&seed={seed}&model=flux"
    with _IMG_SEMAPHORE:
        if time.monotonic() < _POLLINATIONS_COOLDOWN_UNTIL:
            raise AiProviderError("Pollinations đang tạm giới hạn tốc độ IP")
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 Xianglingo-HSK/1.0"},
                timeout=18,
            )
            if resp.status_code == 200:
                ext = _detect_image_ext(resp.content)
                if ext:
                    time.sleep(1.2)
                    return resp.content, ext
            if resp.status_code in (429, 500, 502, 503, 504):
                _POLLINATIONS_COOLDOWN_UNTIL = time.monotonic() + 35.0
            raise AiProviderError(f"Cổng tạo hình trả mã {resp.status_code}")
        except AiProviderError:
            raise
        except Exception as err:
            _POLLINATIONS_COOLDOWN_UNTIL = time.monotonic() + 20.0
            raise AiProviderError("Cổng vẽ AI phản hồi chậm") from err


def _openai_image_bytes(prompt: str, cfg: dict) -> tuple[bytes, str]:
    model = cfg["image_model"] or "gpt-image-1"
    client = get_ai_client().with_options(timeout=MEDIA_TIMEOUT_SECONDS)
    kwargs = {"model": model, "prompt": prompt, "n": 1, "size": "1024x1024"}
    if model.startswith("gpt-image"):
        kwargs.update({"quality": cfg["image_quality"], "output_format": "jpeg"})
        ext = "jpg"
    else:
        kwargs["response_format"] = "b64_json"
        ext = "png"
    response = client.images.generate(**kwargs)
    b64 = response.data[0].b64_json if response.data else None
    if not b64:
        raise AiProviderError("Dịch vụ tạo hình trả về rỗng")
    return base64.b64decode(b64), ext


def image_bytes(prompt: str, keywords: str = "") -> tuple[bytes, str]:
    """Tạo một hình minh họa đề HSK; đảm bảo luôn có hình thật sắc nét (OpenAI -> HuggingFace -> Pollinations -> Wikimedia Commons)."""
    if not image_ready():
        raise AiNotConfiguredError("Chưa sẵn sàng bộ tạo hình AI")
    cfg = current_ai_config()
    want_openai = (
        cfg["image_provider"] == "openai"
        or (
            cfg["image_provider"] not in ("pollinations", "huggingface", "wikimedia", "free")
            and bool(cfg["api_key"] and cfg["image_model"])
            and cfg["image_model"] not in ("pollinations", "flux", "free")
            and is_real_openai_endpoint(cfg["base_url"])
        )
    )
    if want_openai:
        try:
            return _openai_image_bytes(prompt, cfg)
        except Exception:
            pass
    if cfg["hf_api_key"] and cfg["image_provider"] not in ("pollinations", "wikimedia"):
        try:
            return _hf_image_bytes(prompt, cfg["hf_api_key"])
        except Exception:
            pass
    if cfg["image_provider"] != "wikimedia":
        try:
            return _pollinations_image_bytes(prompt)
        except Exception:
            pass
    return _wikimedia_image_bytes(prompt, keywords)


def look_at_image(image: bytes, mime: str, question: str) -> str:
    """Cho model nhìn ảnh và trả lời (tự động dùng Gemini Vision nếu đang cấu hình Gemini)."""
    model = resolve_vision_model()
    if not model:
        raise AiNotConfiguredError("Chưa cấu hình model nhìn ảnh")
    client = get_ai_client().with_options(timeout=MEDIA_TIMEOUT_SECONDS)
    url = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": url}},
            ]}],
        )
        reply = (response.choices[0].message.content or "").strip() if response.choices else ""
    except OpenAIError as error:
        raise AiProviderError("Không gọi được model nhìn ảnh") from error
    except Exception as error:
        raise AiProviderError("Lỗi kết nối model nhìn ảnh") from error
    if not reply:
        raise AiProviderError("Model nhìn ảnh trả về rỗng")
    return reply


def transcribe(audio: bytes, filename: str) -> str:
    """Nghe tệp âm thanh tiếng Trung và chép ra chữ (hỗ trợ Gemini Multimodal Audio, Groq Whisper miễn phí và OpenAI)."""
    mode, model = resolve_stt_mode()
    if not (mode and model):
        raise AiNotConfiguredError("Chưa cấu hình model nghe lại âm thanh")
    client = get_ai_client().with_options(timeout=MEDIA_TIMEOUT_SECONDS)
    if mode == "gemini_chat":
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"
        fmt = ext if ext in ("wav", "mp3", "ogg", "m4a") else "wav"
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请将这段普通话录音准确转写为简体中文，只输出听到的中文句子，不要解释。"},
                        {"type": "input_audio", "input_audio": {"data": base64.b64encode(audio).decode(), "format": fmt}},
                    ],
                }],
            )
            return (response.choices[0].message.content or "").strip() if response.choices else ""
        except OpenAIError as error:
            raise AiProviderError("Không gọi được model nghe Gemini") from error
        except Exception as error:
            raise AiProviderError("Lỗi kết nối model nghe Gemini") from error

    try:
        response = client.audio.transcriptions.create(
            model=model,
            file=(filename, audio),
            language="zh",
            prompt="以下是普通话录音，请用简体中文转写。",
        )
    except OpenAIError as error:
        raise AiProviderError("Không gọi được model nghe") from error
    except Exception as error:
        raise AiProviderError("Lỗi kết nối model nghe") from error
    return (getattr(response, "text", "") or "").strip()
