"""Ghép cả bài Nghe thành MỘT tệp như băng đề HSK thật.

Kịch bản: lời mở đầu -> mỗi phần: lời hướng dẫn -> "第N题" + âm thanh câu (đọc 1 hoặc 2 lần) + khoảng nghỉ
-> "听力考试现在结束。". Lời mở đầu, hướng dẫn, số câu do giọng thứ ba đọc (lời cố định, ghi rõ là thi thử).
Tệp ra: MP3 (cần gói lameenc); chưa cài thì ra WAV. Đọc tệp Giảng viên tự tải lên (mp3/ogg) cần gói miniaudio.
Trả kèm mốc thời gian từng câu để màn duyệt bấm vào câu là nhảy tới đúng đoạn.
"""
import io
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.ai import PCM_RATE, AiNotConfiguredError, AiProviderError, speech_pcm, tts_ready
from app.modules.exam_authoring.services.ai_media_service import AiMediaError, split_lines
from app.modules.exam_authoring.services.hsk_blueprint import BLUEPRINT, level_number
from app.storage.static_media import UPLOADS_DIR

ZH_NUM = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}
# Khoảng nghỉ mặc định sau mỗi câu (giây) theo kiểu câu; Giảng viên chỉnh được theo từng phần
DEFAULT_PAUSE = {"nghe_tranh_dung_sai": 10, "nghe_chon_tranh": 10, "nghe_noi_tranh": 12,
                 "nghe_chon_chu": 15, "nghe_phan_doan": 12, "nghe_doan_2cau": 15}
GAP_REPEAT = 3.0
GAP_AFTER_TEXT = 1.5


def default_pause(part: dict) -> int:
    return max(DEFAULT_PAUSE.get(s["kieu"], 12) for s in part["doan"])


def _silence(seconds: float) -> bytes:
    return b"\x00\x00" * int(PCM_RATE * seconds)


def _decode(path: str) -> bytes:
    """Đọc một tệp âm thanh thành PCM 24 kHz, 16-bit, mono."""
    target = (UPLOADS_DIR / path).resolve()
    if UPLOADS_DIR.resolve() not in target.parents or not target.is_file():
        raise AiMediaError(f"Không tìm thấy tệp âm thanh {path}", 422)
    if path.lower().endswith(".wav"):
        with wave.open(str(target), "rb") as w:
            if w.getframerate() == PCM_RATE and w.getnchannels() == 1 and w.getsampwidth() == 2:
                return w.readframes(w.getnframes())
    try:
        import miniaudio
    except ImportError as error:
        raise AiMediaError("Tệp tự tải lên cần gói miniaudio để ghép (pip install -r requirements.txt)", 503) from error
    try:
        decoded = miniaudio.decode_file(str(target), output_format=miniaudio.SampleFormat.SIGNED16,
                                        nchannels=1, sample_rate=PCM_RATE)
    except Exception as error:
        raise AiMediaError(f"Không đọc được tệp âm thanh {path}", 422) from error
    return decoded.samples.tobytes()


def _encode(pcm: bytes) -> tuple[bytes, str]:
    try:
        import lameenc
    except ImportError:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(PCM_RATE)
            w.writeframes(pcm)
        return buffer.getvalue(), "wav"
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(64)
    encoder.set_in_sample_rate(PCM_RATE)
    encoder.set_channels(1)
    encoder.set_quality(2)
    return bytes(encoder.encode(pcm) + encoder.flush()), "mp3"


def script_for(level: int, parts: list[dict], order: list[list[dict]], pauses: dict[int, int]) -> list[dict]:
    """Danh sách đoạn theo thứ tự phát: {"loai": "loi"|"cau", "noi_dung" | "tep", ...}.
    order[i] = các mục (đã sắp) của phần Nghe thứ i; mỗi mục: {"kieu", "tep_audio", "cau": [...], "so": số câu đầu}."""
    data = BLUEPRINT[level]
    listen = [p for p in parts if p["ky_nang"] == "nghe"]
    total = sum(p["so_cau"] for p in listen)
    plays = data["phat_nghe"]
    lv = ZH_NUM[level]
    seq = [{"loai": "loi", "muc": "mo_dau", "noi_dung": f"大家好！欢迎参加HSK{lv}级模拟考试。"}] * 3
    seq.append({"loai": "loi", "muc": "mo_dau",
                "noi_dung": f"HSK{lv}级听力考试分{ZH_NUM[len(listen)]}部分，共{total}题。请大家注意，听力考试现在开始。"})
    for part, items in zip(listen, order):
        times = "每题听两次。" if plays > 1 else "每题听一次。"
        seq.append({"loai": "loi", "muc": "huong_dan", "phan": part["phan"],
                    "noi_dung": f"第{ZH_NUM[listen.index(part) + 1]}部分，一共{part['so_cau']}个题，{times}"})
        first = True
        pause = pauses.get(part["phan"], default_pause(part))
        for m in items:
            no = m["so"]
            if m["kieu"] == "nghe_noi_tranh":
                children = m.get("cau") or []
                if children:
                    seq.append({"loai": "loi", "muc": "so_cau", "phan": part["phan"],
                                "noi_dung": f"现在开始第{no}到{no + len(children) - 1}题："})
                first = False
                for offset, child in enumerate(children):
                    seq.append(_number(no + offset, False))
                    seq.append({"loai": "cau", "phan": part["phan"], "so": no + offset, "tep": child.get("tep_audio"),
                                "lan": plays, "nghi": pause})
            elif m["kieu"] == "nghe_doan_2cau":
                last = no + len(m.get("cau") or []) - 1
                if first:
                    seq.append(_number(no, True))
                    first = False
                seq.append({"loai": "loi", "muc": "so_cau", "phan": part["phan"],
                            "noi_dung": f"第{no}到{last}题是根据下面一段话："})
                seq.append({"loai": "cau", "phan": part["phan"], "so": no, "den": last, "tep": m.get("tep_audio"),
                            "lan": plays, "nghi": pause * 2})
            else:
                seq.append(_number(no, first))
                first = False
                seq.append({"loai": "cau", "phan": part["phan"], "so": no, "tep": m.get("tep_audio"), "lan": plays, "nghi": pause})
    seq.append({"loai": "loi", "muc": "ket_thuc", "noi_dung": "听力考试现在结束。"})
    return seq


def _number(no: int, first: bool) -> dict:
    return {"loai": "loi", "muc": "so_cau", "noi_dung": f"现在开始第{no}题。" if first else f"第{no}题。"}


def build(level: int, seq: list[dict]) -> dict:
    """Đọc lời cố định, ghép âm thanh câu theo kịch bản; lưu tệp; trả {"duong_dan", "moc": [...], "giay"}."""
    texts = sorted({s["noi_dung"] for s in seq if s["loai"] == "loi"})
    if not tts_ready():
        raise AiMediaError("Bộ tạo giọng đọc AI chưa sẵn sàng nên chưa ghép được bài Nghe", 503)
    missing = [s["so"] for s in seq if s["loai"] == "cau" and not s.get("tep")]
    if missing:
        raise AiMediaError(f"Câu {', '.join(map(str, missing[:10]))} chưa có âm thanh", 422)
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            spoken = dict(zip(texts, pool.map(lambda t: speech_pcm(t, "hoi", level <= 2), texts)))
    except AiNotConfiguredError as error:
        raise AiMediaError("Chưa cấu hình giọng đọc AI", 503) from error
    except AiProviderError as error:
        raise AiMediaError("Dịch vụ giọng đọc đang lỗi, vui lòng ghép lại", 502) from error

    body, marks = bytearray(_silence(1.0)), []
    seconds = lambda: len(body) / 2 / PCM_RATE  # noqa: E731
    for s in seq:
        if s["loai"] == "loi":
            body += spoken[s["noi_dung"]] + _silence(GAP_AFTER_TEXT)
            continue
        clip = _decode(s["tep"])
        start = seconds()
        for turn in range(s["lan"]):
            if turn:
                body += _silence(GAP_REPEAT)
            body += clip
        marks.append({"phan": s["phan"], "so": s["so"], "den": s.get("den", s["so"]),
                      "bat_dau": round(max(0.0, start - 2.0), 1), "ket_thuc": round(seconds(), 1)})
        body += _silence(s["nghi"])
    body += _silence(1.0)
    data, ext = _encode(bytes(body))
    name = f"audio/{uuid.uuid4().hex}.{ext}"
    (UPLOADS_DIR / "audio").mkdir(parents=True, exist_ok=True)
    (UPLOADS_DIR / name).write_bytes(data)
    return {"duong_dan": name, "moc": marks, "giay": round(seconds())}


def _single_script_pcm(script: str, slow: bool) -> bytes:
    """Đọc 1 lượt (plays=1) kịch bản hội thoại 男/女/问 thành PCM 24kHz mono."""
    lines = split_lines(script)
    if not lines:
        raise AiMediaError("Lời nghe trống", 422)
    with ThreadPoolExecutor(max_workers=min(3, len(lines))) as pool:
        chunks = list(pool.map(lambda ln: speech_pcm(ln[1], ln[0] if ln[0] in ("nam", "nu") else "hoi", slow), lines))
    out = bytearray()
    for idx, ((role, _), pcm) in enumerate(zip(lines, chunks)):
        if idx:
            out += _silence(1.2 if role == "hoi" else 0.6)
        out += pcm
    return bytes(out)


def build_for_exam_db(db: Session, bo_de_id: int) -> dict | None:
    """Ghép toàn bộ câu Nghe của một bộ đề trong CSDL thành 1 băng MP3 liên tiếp chuẩn HSK (cập nhật thẳng tep_audio_chung)."""
    exam = db.execute(
        text("""
            SELECT b.id, b.cap_do_id, b.trang_thai, c.ma AS ma_cap, c.ten AS ten_cap
            FROM bo_de b JOIN cap_do c ON c.id = b.cap_do_id
            WHERE b.id = :id AND b.loai = 'de_thi'
        """),
        {"id": bo_de_id},
    ).mappings().first()
    if exam is None:
        raise AiMediaError("Không tìm thấy đề thi", 404)
    level = level_number(exam["ma_cap"], exam["ten_cap"]) or 1

    rows = db.execute(
        text("""
            SELECT i.cau_hoi_id, i.phan, q.cau_cha_id,
                   COALESCE(q.ky_nang, p.ky_nang) AS ky_nang,
                   q.loi_nghe, q.tep_audio, q.noi_dung,
                   p.loi_nghe AS p_loi_nghe, p.tep_audio AS p_tep_audio
            FROM bo_de_cau_hoi i
            JOIN cau_hoi q ON q.id = i.cau_hoi_id
            LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
            WHERE i.bo_de_id = :id AND i.la_cau_vi_du = 0
            ORDER BY i.thu_tu
        """),
        {"id": bo_de_id},
    ).mappings().all()
    db.rollback()  # giải phóng giao dịch đọc trước khi sinh âm thanh

    listen_rows = []
    q_no = 0
    for r in rows:
        q_no += 1
        if r["ky_nang"] == "nghe":
            listen_rows.append({**dict(r), "so": q_no})
    if not listen_rows:
        return None
    if not tts_ready():
        raise AiMediaError("Bộ tạo giọng đọc AI chưa sẵn sàng", 503)

    data_bp = BLUEPRINT.get(level, BLUEPRINT[1])
    plays = data_bp["phat_nghe"]
    slow = level <= 2
    lv_zh = ZH_NUM.get(level, "一")

    # Gom theo phần (phan) giữ nguyên thứ tự xuất hiện trong đề
    parts_grouped: list[tuple[int, list[dict]]] = []
    for r in listen_rows:
        phan = int(r["phan"] or 1)
        if not parts_grouped or parts_grouped[-1][0] != phan:
            parts_grouped.append((phan, [r]))
        else:
            parts_grouped[-1][1].append(r)

    narrator_texts: set[str] = {
        f"大家好！欢迎参加HSK{lv_zh}级模拟考试。",
        f"HSK{lv_zh}级听力考试分{ZH_NUM.get(len(parts_grouped), str(len(parts_grouped)))}部分，共{len(listen_rows)}题。请大家注意，听力考试现在开始。",
        "听力考试现在结束。",
    }
    plan_steps: list[dict] = (
        [{"loai": "loi", "text": f"大家好！欢迎参加HSK{lv_zh}级模拟考试。"}] * (3 if level <= 2 else 1)
        + [{"loai": "loi", "text": f"HSK{lv_zh}级听力考试分{ZH_NUM.get(len(parts_grouped), str(len(parts_grouped)))}部分，共{len(listen_rows)}题。请大家注意，听力考试现在开始。"}]
    )

    for idx_part, (phan, p_items) in enumerate(parts_grouped, start=1):
        times_zh = "每题听两次。" if plays > 1 else "每题听一次。"
        header_txt = f"第{ZH_NUM.get(idx_part, str(idx_part))}部分，一共{len(p_items)}个题，{times_zh}"
        narrator_texts.add(header_txt)
        plan_steps.append({"loai": "loi", "text": header_txt})

        bp_part = next((bp for bp in data_bp["phan"] if bp["phan"] == phan and bp["ky_nang"] == "nghe"), None)
        pause = default_pause(bp_part) if bp_part else (10 if level <= 2 else 13)
        first = True
        cursor = 0
        while cursor < len(p_items):
            cur = p_items[cursor]
            # Đoạn nghe chung nhiều câu hỏi (ví dụ HSK 4 phần 3: ngữ liệu cha có lời nghe/audio chung, câu con không có audio riêng)
            if cur["cau_cha_id"] and not cur["tep_audio"] and (cur["p_loi_nghe"] or cur["p_tep_audio"]):
                group = [cur]
                while (cursor + len(group) < len(p_items)
                       and p_items[cursor + len(group)]["cau_cha_id"] == cur["cau_cha_id"]):
                    group.append(p_items[cursor + len(group)])
                start_no, end_no = group[0]["so"], group[-1]["so"]
                if first:
                    t0 = f"现在开始第{start_no}题。"
                    narrator_texts.add(t0)
                    plan_steps.append({"loai": "loi", "text": t0})
                    first = False
                if end_no > start_no:
                     lead = f"第{start_no}到{end_no}题是根据下面一段话："
                     narrator_texts.add(lead)
                     plan_steps.append({"loai": "loi", "text": lead})
                plan_steps.append({
                    "loai": "clip", "phan": phan, "so": start_no, "den": end_no,
                    "script": cur["p_loi_nghe"], "tep": cur["p_tep_audio"],
                    "lan": plays, "nghi": pause * max(1, len(group)),
                })
                cursor += len(group)
                continue

            no_txt = f"现在开始第{cur['so']}题。" if first else f"第{cur['so']}题。"
            first = False
            narrator_texts.add(no_txt)
            plan_steps.append({"loai": "loi", "text": no_txt})
            plan_steps.append({
                "loai": "clip", "phan": phan, "so": cur["so"], "den": cur["so"],
                "script": cur["loi_nghe"] or cur["p_loi_nghe"],
                "tep": cur["tep_audio"] or cur["p_tep_audio"],
                "lan": plays, "nghi": pause,
            })
            cursor += 1

    plan_steps.append({"loai": "loi", "text": "听力考试现在结束。"})

    try:
        sorted_narr = sorted(narrator_texts)
        with ThreadPoolExecutor(max_workers=3) as pool:
            spoken_narr = dict(zip(sorted_narr, pool.map(lambda t: speech_pcm(t, "hoi", slow), sorted_narr)))
    except (AiNotConfiguredError, AiProviderError) as err:
        raise AiMediaError(str(err) or "Không tạo được lời dẫn băng Nghe", 502) from err

    body, marks = bytearray(_silence(1.0)), []
    seconds = lambda: len(body) / 2 / PCM_RATE  # noqa: E731
    for s in plan_steps:
        if s["loai"] == "loi":
            body += spoken_narr[s["text"]] + _silence(GAP_AFTER_TEXT)
            continue
        if s.get("script"):
            try:
                clip = _single_script_pcm(s["script"], slow)
            except (AiMediaError, AiNotConfiguredError, AiProviderError):
                if not s.get("tep"):
                    raise AiMediaError(f"Câu {s['so']} chưa có lời nghe hoặc tệp âm thanh", 422)
                clip = _decode(s["tep"])
                s["lan"] = 1  # tệp lẻ câu hỏi trong ngân hàng đã chứa sẵn số lần lặp
        elif s.get("tep"):
            clip = _decode(s["tep"])
            s["lan"] = 1
        else:
            raise AiMediaError(f"Câu {s['so']} chưa có lời nghe hoặc tệp âm thanh", 422)

        start = seconds()
        for turn in range(s["lan"]):
            if turn:
                body += _silence(GAP_REPEAT)
            body += clip
        marks.append({
            "phan": s["phan"], "so": s["so"], "den": s["den"],
            "bat_dau": round(max(0.0, start - 2.0), 1), "ket_thuc": round(seconds(), 1),
        })
        body += _silence(s["nghi"])

    body += _silence(1.0)
    data, ext = _encode(bytes(body))
    name = f"audio/{uuid.uuid4().hex}.{ext}"
    (UPLOADS_DIR / "audio").mkdir(parents=True, exist_ok=True)
    (UPLOADS_DIR / name).write_bytes(data)

    db.execute(text("UPDATE bo_de SET tep_audio_chung = :p WHERE id = :id"), {"p": name, "id": bo_de_id})
    db.commit()
    return {"duong_dan": name, "moc": marks, "giay": round(seconds()), "so_cau_nghe": len(listen_rows)}
