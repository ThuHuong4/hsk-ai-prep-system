"""Bộ hàm dùng chung để tổng hợp băng nghe MP3 chuẩn HSK 2.0 (đa giọng đọc, có đệm đĩa) và nạp đề mô phỏng."""
import asyncio
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import edge_tts
import lameenc
import miniaudio
from sqlalchemy import text

from app.database.session import SessionLocal
from app.integrations.ai.config import current_ai_config
from app.modules.exam_authoring.schemas.exam_payload import ExamInfoIn, ExamItemIn
from app.modules.exam_authoring.services import exam_service
from app.modules.questions.schemas.question_payload import QuestionIn
from app.modules.questions.services.question_rules import validate_question
from app.modules.questions.services.question_status import publish_question
from app.modules.questions.services.save_question import create_question

import tempfile
BACKEND = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND / "scripts" / "data"
UPLOADS = BACKEND / "uploads"
CACHE_DIR = Path(tempfile.gettempdir()) / "xianglingo_tts_cache"
PCM_RATE = 24000
ZH_NUM = {1: "一", 2: "二", 3: "三", 4: "四"}
LETTER = {c: i + 1 for i, c in enumerate("ABCDEF")}
_SPEAKER_RE = re.compile(r"^\s*(男|女|问|問)\s*[：:]\s*")


def tf(ok: bool) -> list[dict]:
    return [{"noi_dung": "Đúng", "la_dap_an_dung": ok}, {"noi_dung": "Sai", "la_dap_an_dung": not ok}]


def opts_text(items: list[str], ans_letter: str | None = None) -> list[dict]:
    ans_idx = (LETTER[ans_letter] - 1) if ans_letter else None
    return [{"noi_dung": s, "la_dap_an_dung": i == ans_idx} for i, s in enumerate(items)]


def opts_paths(paths: list[str], ans_letter: str | None = None) -> list[dict]:
    ans_idx = (LETTER[ans_letter] - 1) if ans_letter else None
    return [{"tep_hinh": p, "la_dap_an_dung": i == ans_idx} for i, p in enumerate(paths)]


def silence(sec: float) -> bytes:
    return b"\x00\x00" * int(PCM_RATE * sec)


def clean_tts_text(raw: str) -> str:
    txt = (raw or "").replace("★", "").strip()
    # Bỏ khoảng trắng thừa giữa các chữ Hán để TTS đọc tự nhiên liền mạch
    txt = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff0-9])", "", txt)
    txt = re.sub(r"(?<=[0-9])\s+(?=[\u4e00-\u9fff])", "", txt)
    txt = re.sub(r"\s+([，。？！、：；])", r"\1", txt)
    return txt.strip()


def parse_dialogue(script: str, alt_idx: int = 0) -> list[tuple[str, str, float]]:
    """Trả danh sách [(role, cleaned_text, pre_gap_sec)] cho một câu nghe."""
    out: list[tuple[str, str, float]] = []
    default_primary = "nu" if alt_idx % 2 == 0 else "nam"
    for raw in (script or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("★"):
            cleaned = clean_tts_text(line)
            if cleaned:
                out.append(("hoi", cleaned, 1.1 if out else 0.0))
            continue
        m = _SPEAKER_RE.match(line)
        if m:
            tag = m.group(1)
            role = {"男": "nam", "女": "nu"}.get(tag, "hoi")
            cleaned = clean_tts_text(line[m.end():])
            gap = (1.1 if role == "hoi" else 0.55) if out else 0.0
        else:
            role = default_primary
            cleaned = clean_tts_text(line)
            gap = 0.6 if out else 0.0
        if cleaned:
            out.append((role, cleaned, gap))
    return out


def build_tape_plan(data: dict) -> list[tuple]:
    """Xây kịch bản ghép băng nghe chuẩn HSK 2.0 cho một bộ đề."""
    lv_str = data["exam"]["level"]
    level = int(lv_str.replace("HSK", ""))
    slow = level <= 2
    plays = 2 if level <= 3 else 1
    lv_zh = ZH_NUM[level]

    # Thu thập các mục nghe tính điểm theo từng phần
    part_map: dict[int, list[dict]] = {}
    q_no = 0
    for entry in data["plan"]:
        part = entry["part"]
        if "group" in entry:
            g = entry["group"]
            if g["ky_nang"] != "nghe":
                for _, is_ex in entry["children"]:
                    if not is_ex:
                        q_no += 1
                continue
            scored_children = []
            for child, is_ex in entry["children"]:
                if not is_ex:
                    q_no += 1
                    scored_children.append((q_no, child))
            if not scored_children:
                continue
            if g.get("loi_nghe"):
                # Đoạn văn chung 2 câu (HSK 4 phần 3 câu 36–45)
                part_map.setdefault(part, []).append({
                    "kind": "passage_group",
                    "start": scored_children[0][0],
                    "end": scored_children[-1][0],
                    "passage": g["loi_nghe"],
                    "qs": [(no, c["loi_nghe"]) for no, c in scored_children],
                })
            else:
                # Nhóm nối tranh (HSK 1 phần 3, HSK 2 phần 2, HSK 3 phần 1)
                part_map.setdefault(part, []).append({
                    "kind": "image_group",
                    "start": scored_children[0][0],
                    "end": scored_children[-1][0],
                    "qs": [(no, c["loi_nghe"]) for no, c in scored_children],
                })
        else:
            q = entry["q"]
            is_ex = bool(entry.get("ex"))
            if is_ex:
                continue
            q_no += 1
            if q["ky_nang"] == "nghe":
                part_map.setdefault(part, []).append({
                    "kind": "single",
                    "no": q_no,
                    "script": q["loi_nghe"],
                })

    total_listen = sum(
        len(it["qs"]) if "qs" in it else 1
        for items in part_map.values()
        for it in items
    )
    parts_sorted = sorted(part_map.items(), key=lambda kv: kv[0])
    steps: list[tuple] = []

    greet = f"大家好！欢迎参加HSK（{lv_zh}级）模拟考试。"
    for _ in range(3):
        steps.append(("line", "hoi", slow, greet, 0.9))
    intro = f"HSK（{lv_zh}级）听力考试分{ZH_NUM[len(parts_sorted)]}部分，共{total_listen}题。请大家注意，听力考试现在开始。"
    steps.append(("line", "hoi", slow, intro, 1.4))

    pause_sec = 5.0 if level <= 2 else 6.0
    alt_counter = 0

    for p_idx, (_, p_items) in enumerate(parts_sorted, start=1):
        p_count = sum(len(it["qs"]) if "qs" in it else 1 for it in p_items)
        times_zh = "每题听两次。" if plays > 1 else "每题听一次。"
        steps.append(("line", "hoi", slow, f"第{ZH_NUM[p_idx]}部分。一共{p_count}个题，{times_zh}", 1.2))
        first_in_part = True

        for it in p_items:
            if it["kind"] == "image_group":
                steps.append(("line", "hoi", slow, f"现在开始第{it['start']}到{it['end']}题：", 1.0))
                first_in_part = False
                for no, sc in it["qs"]:
                    alt_counter += 1
                    steps.append(("line", "hoi", slow, f"第{no}题。", 0.6))
                    steps.append(("dialogue", slow, plays, parse_dialogue(sc, alt_counter), pause_sec))
            elif it["kind"] == "passage_group":
                alt_counter += 1
                first_in_part = False
                steps.append(("line", "hoi", slow, f"第{it['start']}到{it['end']}题是根据下面一段话：", 0.9))
                p_role = "nam" if alt_counter % 2 == 0 else "nu"
                steps.append(("line", p_role, slow, clean_tts_text(it["passage"]), 1.1))
                for no, q_sc in it["qs"]:
                    steps.append(("line", "hoi", slow, f"第{no}题：{clean_tts_text(q_sc)}", pause_sec))
            else:
                alt_counter += 1
                no = it["no"]
                lbl = f"现在开始第{no}题：" if first_in_part else f"第{no}题。"
                first_in_part = False
                steps.append(("line", "hoi", slow, lbl, 0.6))
                steps.append(("dialogue", slow, plays, parse_dialogue(it["script"], alt_counter), pause_sec))

    steps.append(("line", "hoi", slow, "听力考试现在结束。", 1.0))
    return steps


def _cache_file(role: str, slow: bool, text_val: str) -> Path:
    key = f"{role}|{'slow' if slow else 'norm'}|{text_val}".encode("utf-8")
    return CACHE_DIR / f"{hashlib.sha1(key).hexdigest()}.pcm"


async def _synth_one(sem: asyncio.Semaphore, cfg: dict, role: str, slow: bool, text_val: str) -> None:
    cfile = _cache_file(role, slow, text_val)
    if cfile.is_file() and cfile.stat().st_size > 400:
        return
    voice = {
        "nam": cfg["edge_voice_nam"],
        "nu": cfg["edge_voice_nu"],
    }.get(role, cfg["edge_voice_hoi"])
    rate = "-14%" if slow else "-4%"

    async with sem:
        for attempt in range(5):
            try:
                comm = edge_tts.Communicate(text_val, voice, rate=rate)
                mp3_buf = bytearray()
                async for chunk in comm.stream():
                    if chunk.get("type") == "audio" and chunk.get("data"):
                        mp3_buf.extend(chunk["data"])
                if not mp3_buf:
                    raise RuntimeError("Empty audio stream")
                decoded = miniaudio.decode(
                    bytes(mp3_buf),
                    output_format=miniaudio.SampleFormat.SIGNED16,
                    nchannels=1,
                    sample_rate=PCM_RATE,
                )
                pcm = decoded.samples.tobytes()
                cfile.write_bytes(pcm)
                return
            except Exception as exc:
                if attempt == 4:
                    raise RuntimeError(f"TTS lỗi cho câu '{text_val[:30]}': {exc}") from exc
                await asyncio.sleep(1.2 * (attempt + 1))


def encode_mp3(pcm: bytes) -> bytes:
    enc = lameenc.Encoder()
    enc.set_bit_rate(64)
    enc.set_in_sample_rate(PCM_RATE)
    enc.set_channels(1)
    enc.set_quality(2)
    return bytes(enc.encode(pcm) + enc.flush())


def synthesize_exam_tapes(specs: list[dict]) -> None:
    """Tổng hợp song song mọi câu thoại duy nhất và đóng gói MP3 cho các đề chưa có băng nghe."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cfg = current_ai_config()

    pending_plans: list[tuple[dict, Path, list[tuple]]] = []
    unique_jobs: set[tuple[str, bool, str]] = set()

    for data in specs:
        out_mp3 = UPLOADS / data["exam"]["audio"]
        if out_mp3.is_file() and out_mp3.stat().st_size > 100_000:
            print(f"· Đã có sẵn băng nghe {data['exam']['audio']} ({out_mp3.stat().st_size // 1024} KB)")
            continue
        steps = build_tape_plan(data)
        pending_plans.append((data, out_mp3, steps))
        for st in steps:
            if st[0] == "line":
                _, role, slow, txt, _ = st
                unique_jobs.add((role, slow, txt))
            elif st[0] == "dialogue":
                _, slow, _, turns, _ = st
                for role, txt, _ in turns:
                    unique_jobs.add((role, slow, txt))

    if not pending_plans:
        return

    uncached = [j for j in sorted(unique_jobs) if not (_cache_file(*j).is_file() and _cache_file(*j).stat().st_size > 400)]
    print(f"→ Cần tổng hợp {len(uncached)}/{len(unique_jobs)} câu thoại Mandarin mới cho {len(pending_plans)} băng nghe...")

    if uncached:
        async def _runner() -> None:
            sem = asyncio.Semaphore(10)
            await asyncio.gather(*(_synth_one(sem, cfg, r, sl, tx) for r, sl, tx in uncached))

        asyncio.run(_runner())

    for data, out_mp3, steps in pending_plans:
        out_mp3.parent.mkdir(parents=True, exist_ok=True)
        body = bytearray(silence(0.8))
        for st in steps:
            if st[0] == "line":
                _, role, slow, txt, post_gap = st
                body += _cache_file(role, slow, txt).read_bytes()
                body += silence(post_gap)
            elif st[0] == "dialogue":
                _, slow, plays, turns, post_pause = st
                clip = bytearray()
                for role, txt, pre_gap in turns:
                    if pre_gap > 0:
                        clip += silence(pre_gap)
                    clip += _cache_file(role, slow, txt).read_bytes()
                clip_bytes = bytes(clip)
                for turn_idx in range(plays):
                    if turn_idx > 0:
                        body += silence(2.2)
                    body += clip_bytes
                body += silence(post_pause)
        body += silence(1.0)
        mp3_bytes = encode_mp3(bytes(body))
        out_mp3.write_bytes(mp3_bytes)
        dur_min = round(len(body) / 2 / PCM_RATE / 60, 1)
        print(f"✓ Đã ghép băng nghe {data['exam']['audio']} ({len(mp3_bytes) // 1024} KB, ~{dur_min} phút)")


def save_and_seed_exams(specs: list[tuple[str, dict]]) -> None:
    """Lưu JSON chuẩn, ghép băng nghe MP3, kiểm tra media & quy tắc câu hỏi rồi xuất bản vào CSDL."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for fname, payload in specs:
        (DATA_DIR / fname).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    # Kiểm tra trước toàn bộ câu hỏi và tệp hình ảnh (trước khi tốn thời gian TTS nếu có lỗi cú pháp!)
    db = SessionLocal()
    try:
        level_map = {r[0]: int(r[1]) for r in db.execute(text("SELECT ma, id FROM cap_do")).all()}
    finally:
        db.close()

    for _, data in specs:
        exam = data["exam"]
        lv_id = level_map[exam["level"]]
        img_paths = []
        for idx, entry in enumerate(data["plan"], start=1):
            if "group" in entry:
                body = {**entry["group"], "cap_do_id": lv_id, "cau_con": [c for c, _ in entry["children"]]}
                objs = [entry["group"]] + [c for c, _ in entry["children"]]
            else:
                body = {**entry["q"], "cap_do_id": lv_id}
                objs = [entry["q"]]
            for o in objs:
                img_paths += [o.get("tep_hinh")] + [ op.get("tep_hinh") for op in o.get("phuong_an", []) ]
            try:
                q_in = QuestionIn(**body)
                validate_question(q_in)
            except Exception as exc:
                raise RuntimeError(f"Lỗi cấu trúc tại {exam['code']} mục {idx} (phần {entry['part']}): {exc}") from exc

        missing_imgs = sorted({p for p in img_paths if p and not (UPLOADS / p).is_file()})
        if missing_imgs:
            raise RuntimeError(f"Thiếu ảnh trong {exam['code']}: {missing_imgs[:5]}")

    # Tổng hợp băng nghe MP3
    synthesize_exam_tapes([payload for _, payload in specs])

    # Ghi vào CSDL
    db = SessionLocal()
    try:
        lecturer_id = int(db.execute(
            text("SELECT u.id FROM nguoi_dung u JOIN vai_tro v ON v.id = u.vai_tro_id WHERE v.ma = 'giang_vien' ORDER BY u.id DESC LIMIT 1")
        ).scalar_one())
        for _, data in specs:
            exam = data["exam"]
            if db.execute(text("SELECT 1 FROM bo_de WHERE ma_de = :m"), {"m": exam["code"]}).first():
                print(f"· Bỏ qua {exam['ten']} ({exam['code']}): đã tồn tại trong CSDL")
                continue
            lv_id = level_map[exam["level"]]
            assert (UPLOADS / exam["audio"]).is_file(), f"Thiếu audio {exam['audio']}"

            items: list[ExamItemIn] = []
            for entry in data["plan"]:
                part = entry["part"]
                if "group" in entry:
                    body = {**entry["group"], "cap_do_id": lv_id, "cau_con": [c for c, _ in entry["children"]]}
                    qid = create_question(db, QuestionIn(**body), lecturer_id)
                    publish_question(db, qid, lecturer_id)
                    child_ids = [int(r[0]) for r in db.execute(
                        text("SELECT id FROM cau_hoi WHERE cau_cha_id = :p ORDER BY id"), {"p": qid}
                    ).all()]
                    for cid, (_, is_ex) in zip(child_ids, entry["children"]):
                        items.append(ExamItemIn(cau_hoi_id=cid, phan=part, la_cau_vi_du=bool(is_ex)))
                else:
                    body = {**entry["q"], "cap_do_id": lv_id}
                    qid = create_question(db, QuestionIn(**body), lecturer_id)
                    publish_question(db, qid, lecturer_id)
                    items.append(ExamItemIn(cau_hoi_id=qid, phan=part, la_cau_vi_du=bool(entry.get("ex"))))

            exam_id = exam_service.create_exam(db, ExamInfoIn(
                cap_do_id=lv_id,
                ten=exam["ten"],
                ma_de=exam["code"],
                thoi_luong_phut=exam["phut"],
                nguon=exam["nguon"],
                tep_audio_chung=exam["audio"],
            ), lecturer_id)
            exam_service.set_exam_items(db, exam_id, items)
            exam_service.publish_exam(db, exam_id)
            scored = sum(1 for i in items if not i.la_cau_vi_du)
            print(f"→ Đã nạp & đăng {exam['ten']} ({exam['code']}): {scored} câu tính điểm, {len(items) - scored} câu ví dụ.")
    finally:
        db.close()
