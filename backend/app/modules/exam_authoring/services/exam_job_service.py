"""Phiên "Tạo đề hoàn chỉnh với AI" chạy nền; Giảng viên chỉ xem lại và duyệt.

Các bước (mỗi bước làm lại được, chạy tiếp được nếu máy chủ khởi động lại giữa chừng):
  1. Soạn nội dung mọi phần  2. Kiểm định nội dung (AI phản biện, AI giải lại đề, code dò từ vượt cấp)
  3. Tự sửa mục có lỗi (tối đa 2 vòng)  4. Tạo hình + AI nhìn lại ảnh  5. Tạo giọng đọc + máy nghe lại
  6. Ghép cả bài Nghe thành 1 tệp  -> chờ Giảng viên duyệt.
Tiến trình lưu bằng tệp JSON trong private_uploads/ai_de (không đổi CSDL, không phục vụ công khai).
Chỉ bước Duyệt mới ghi CSDL: lưu + đăng câu (ghi người duyệt), tạo đề kèm âm thanh chung, đăng đề.
Giảng viên chỉ thấy phiên của chính mình.
"""
import json
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from types import SimpleNamespace

from app.database.session import SessionLocal
from app.integrations.ai import ai_ready, image_ready, is_real_openai_endpoint, stt_ready, tts_ready, vision_ready
from app.modules.exam_authoring.schemas.exam_payload import ExamInfoIn, ExamItemIn
from app.modules.exam_authoring.services import ai_part_service as parts_svc
from app.modules.exam_authoring.services import exam_checks as checks
from app.modules.exam_authoring.services import listening_audio
from app.modules.exam_authoring.services.ai_media_service import AiMediaError, make_audio, make_image, translate_scenes_batch
from app.modules.exam_authoring.services.exam_service import create_exam, delete_draft_exam, publish_exam, set_exam_items
from app.modules.exam_authoring.services.hsk_blueprint import BLUEPRINT, KINDS
from app.modules.questions.schemas.question_payload import _MEDIA_PATH
from app.modules.questions.services.ai_draft_service import AiDraftError
from app.modules.questions.services.errors import ConflictError
from app.modules.questions.services.question_rules import QuestionRuleError
from app.storage.private_files import PRIVATE_DIR
from app.storage.static_media import UPLOADS_DIR

JOB_DIR = PRIVATE_DIR / "ai_de"
_ID = re.compile(r"^[0-9a-f]{32}$")
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ai-de")
_RUNNING: set[str] = set()
_APPROVING: set[str] = set()
_LOCKS: dict[str, threading.Lock] = {}
_GLOBAL = threading.Lock()
STEPS = ["Soạn nội dung", "Kiểm định nội dung", "Tự sửa lỗi", "Tạo hình", "Tạo giọng đọc", "Ghép bài Nghe"]
FIX_ROUNDS = 2


class JobError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------- lưu trữ

def _lock(job_id: str) -> threading.Lock:
    with _GLOBAL:
        return _LOCKS.setdefault(job_id, threading.Lock())


def _file(job_id: str):
    if not _ID.fullmatch(job_id or ""):
        raise JobError("Không tìm thấy phiên soạn đề", 404)
    return JOB_DIR / f"{job_id}.json"


def _read(job_id: str) -> dict:
    path = _file(job_id)
    if not path.is_file():
        raise JobError("Không tìm thấy phiên soạn đề", 404)
    return json.loads(path.read_text(encoding="utf-8"))


def _write(job: dict) -> None:
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    job["cap_nhat_luc"] = datetime.now().isoformat(timespec="seconds")
    path = _file(job["id"])
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)  # ghi nguyên khối: người đọc không bao giờ thấy tệp ghi dở


def _owned(job_id: str, lecturer_id: int) -> dict:
    job = _read(job_id)
    if job.get("nguoi_tao_id") != lecturer_id:
        raise JobError("Không tìm thấy phiên soạn đề", 404)
    return job


def _mutate(job_id: str, fn) -> dict:
    """Đọc - sửa - ghi trong khóa của phiên (không giữ khóa lúc chờ AI)."""
    with _lock(job_id):
        job = _read(job_id)
        fn(job)
        _write(job)
        return job


# ---------------------------------------------------------------- tiện ích mục

def slots(m: dict) -> list[dict]:
    """Ô tệp của một mục (khớp mediaSlots ở giao diện)."""
    out = []
    if "tep_hinh" in m:
        out.append({"path": ["tep_hinh"], "loai": "hinh", "nguon": m.get("mo_ta_hinh")})
    if "tep_audio" in m:
        out.append({"path": ["tep_audio"], "loai": "audio", "nguon": m.get("loi_nghe")})
    for i, o in enumerate(m.get("lua_chon") or []):
        if "tep_hinh" in o:
            out.append({"path": ["lua_chon", i, "tep_hinh"], "loai": "hinh", "nguon": o.get("mo_ta_hinh")})
    for i, c in enumerate(m.get("cau") or []):
        if "tep_audio" in c:
            out.append({"path": ["cau", i, "tep_audio"], "loai": "audio", "nguon": c.get("loi_nghe")})
    return out


def _sid(path: list) -> str:
    return ".".join(str(p) for p in path)


def _get(obj, path):
    for key in path:
        obj = obj[key]
    return obj


def _set(obj, path, value) -> None:
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value


def _new_card(raw: dict, phan: int) -> dict:
    return {"key": uuid.uuid4().hex[:12], "phan": phan, "ban": 1, "muc": raw["muc"], "loi": raw.get("loi"),
            "van_de_ai": raw.get("van_de_ai"), "trung_lap": raw.get("trung_lap") or [], "so_cau": raw.get("so_cau", 1),
            "giai_lai": None, "tu_ngoai_cap": [], "kiem_hinh": {}, "kiem_am": {}, "da_xem": False,
            "trao_doi": [], "duyet": None, "loi_duyet": None}


def _replace_content(card: dict, raw: dict) -> None:
    card.update({"muc": raw["muc"], "loi": raw.get("loi"), "van_de_ai": raw.get("van_de_ai"),
                 "trung_lap": raw.get("trung_lap") or [], "giai_lai": None, "tu_ngoai_cap": [], "da_xem": False,
                 "loi_duyet": None, "ban": card.get("ban", 1) + 1})
    alive = {_sid(s["path"]) for s in slots(card["muc"]) if _get(card["muc"], s["path"])}
    card["kiem_hinh"] = {k: v for k, v in card.get("kiem_hinh", {}).items() if k in alive}
    card["kiem_am"] = {k: v for k, v in card.get("kiem_am", {}).items() if k in alive}


def _part(job: dict, phan: int) -> dict:
    return next(p for p in BLUEPRINT[job["level"]]["phan"] if p["phan"] == phan)


def ordered_cards(job: dict, phan: int) -> list[dict]:
    order = [s["kieu"] for s in _part(job, phan)["doan"]]
    cards = [c for c in job["the"] if c["phan"] == phan]
    return sorted(cards, key=lambda c: order.index(c["muc"]["kieu"]))


def numbering(job: dict) -> dict[str, int]:
    """Số câu đầu của mỗi mục, đánh liên tục cả đề như đề thật."""
    result, n = {}, 1
    for part in BLUEPRINT[job["level"]]["phan"]:
        cursor = n
        for c in ordered_cards(job, part["phan"]):
            result[c["key"]] = cursor
            cursor += c["so_cau"]
        n += part["so_cau"]
    return result


def light(card: dict) -> tuple[str, list[str], list[str]]:
    """Đèn: do = chặn duyệt; vang = cần nhìn kỹ; xanh = qua mọi lớp kiểm tra."""
    m = card["muc"]
    red, yellow = [], []
    if card.get("loi"):
        red.append(f"Thiếu thành phần: {card['loi']}")
    lack = parts_svc.missing_media(m)
    if lack:
        red.append("Còn thiếu " + ", ".join(lack))
    if card.get("loi_duyet"):
        red.append(card["loi_duyet"])
    if card.get("van_de_ai") is None:
        yellow.append("AI phản biện chưa soát được mục này")
    elif card["van_de_ai"]:
        yellow += [f"AI phản biện: {v}" for v in card["van_de_ai"]]
    solved = card.get("giai_lai")
    if m["kieu"] != "viet_tranh":
        if solved is None:
            yellow.append("Chưa giải lại đề tự động được")
        elif not solved.get("ok"):
            yellow.append(f"AI giải lại ra đáp án khác ({json.dumps(solved.get('ai'), ensure_ascii=False)}): {solved.get('ly_do', '')}")
    if card.get("tu_ngoai_cap"):
        yellow.append("Chữ/từ không có trong bảng từ vựng tới cấp này: " + "、".join(card["tu_ngoai_cap"]))
    if card.get("trung_lap"):
        yellow.append(f"Gần trùng {len(card['trung_lap'])} câu đã có trong ngân hàng")
    for s in slots(m):
        sid = _sid(s["path"])
        if not _get(m, s["path"]):
            continue
        result = ((card.get("kiem_hinh") if s["loai"] == "hinh" else card.get("kiem_am")) or {}).get(sid)
        name = "hình" if s["loai"] == "hinh" else "âm thanh"
        where = "" if len(s["path"]) == 1 else (f" {chr(65 + s['path'][1])}" if s["path"][0] == "lua_chon" else f" câu con {s['path'][1] + 1}")
        if result is None:
            yellow.append(f"Chưa kiểm {name}{where} tự động")
        elif s["loai"] == "hinh" and (not result.get("khop") or result.get("co_chu")):
            yellow.append(f"Ảnh{where}: {'có chữ trong ảnh; ' if result.get('co_chu') else ''}{result.get('nhan_xet') or 'có thể chưa khớp'}")
        elif s["loai"] == "audio" and result.get("do_khop", 0) < checks.AUDIO_MATCH:
            yellow.append(f"Máy nghe lại{where} lệch ({int(result['do_khop'] * 100)}%): {result.get('nghe_duoc', '')}")
    return ("do" if red else "vang" if yellow else "xanh"), red, yellow


# ---------------------------------------------------------------- kiểm định & tạo tệp cho một mục

def _check_content(card: dict, vocab: set[str], level_name: str) -> None:
    card["tu_ngoai_cap"] = checks.outside_words(card["muc"], vocab)
    card["giai_lai"] = checks.solve_check([card["muc"]], level_name)[0]


def _make_slot(card: dict, slot: dict, level: int) -> None:
    """Tạo một tệp + kiểm tự động; kiểm không đạt thì tạo lại 1 lần."""
    sid, m = _sid(slot["path"]), card["muc"]
    for attempt in range(2):
        try:
            if slot["loai"] == "hinh":
                path = make_image(slot["nguon"] or "")
                result = checks.image_check(path, slot["nguon"])
                good = result is None or (result["khop"] and not result["co_chu"])
            else:
                path = make_audio(slot["nguon"] or "", plays=1, slow=level <= 2)
                result = checks.audio_check(path, slot["nguon"])
                good = result is None or result["do_khop"] >= checks.AUDIO_MATCH
        except AiMediaError:
            if attempt:
                return
            continue
        _set(m, slot["path"], path)
        (card.setdefault("kiem_hinh", {}) if slot["loai"] == "hinh" else card.setdefault("kiem_am", {}))[sid] = result
        if good:
            return


def _fill_media(card: dict, level: int, only: str | None = None) -> None:
    for slot in slots(card["muc"]):
        if (only is None or only == slot["loai"]) and not _get(card["muc"], slot["path"]):
            _make_slot(card, slot, level)


# ---------------------------------------------------------------- chạy nền

def _progress(job: dict, step: int, detail: str = "") -> None:
    job["trang_thai"] = "dang_chay"
    job["buoc"] = {"so": step + 1, "tong": len(STEPS), "ten": STEPS[step], "chi_tiet": detail}
    _write(job)


def _missing_segments(job: dict) -> list[tuple[int, str, int]]:
    need = []
    for part in BLUEPRINT[job["level"]]["phan"]:
        for seg in part["doan"]:
            have = sum(1 for c in job["the"] if c["phan"] == part["phan"] and c["muc"]["kieu"] == seg["kieu"])
            lack = seg["so_cau"] // KINDS[seg["kieu"]][1] - have
            if lack > 0:
                need.append((part["phan"], seg["kieu"], lack))
    return need


def _generate(job: dict, mutex: threading.Lock) -> None:
    for pass_no in range(3):
        need = _missing_segments(job)
        if not need:
            return
        if pass_no > 0:
            time.sleep(3.5 * pass_no)
        done = [0]

        def work(item, total_groups=len(need)):
            phan, kieu, lack = item
            db = SessionLocal()
            try:
                others = [checks._texts(c["muc"])[0][:160] for c in job["the"] if c["phan"] == phan and checks._texts(c["muc"])][:25]
                body = SimpleNamespace(cap_do_id=job["cap_do_id"], phan=phan, kieu=kieu, so_muc=lack,
                                       chu_de=job.get("chu_de"), yeu_cau=job.get("yeu_cau"), tranh=others)
                try:
                    cards = parts_svc.generate_part(db, body, with_review=False)["the"][:lack]
                except AiDraftError:
                    cards = []
            finally:
                db.close()
            with mutex:
                job["the"] += [_new_card(c, phan) for c in cards]
                done[0] += 1
                _progress(job, 0, f"{done[0]}/{total_groups} nhóm câu")

        workers = (3 if is_real_openai_endpoint() else 2) if pass_no == 0 else 1
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(work, need))


def _problems(card: dict) -> list[str]:
    issues = list(card.get("van_de_ai") or [])
    if card.get("loi"):
        issues.append(f"Thiếu thành phần: {card['loi']}")
    solved = card.get("giai_lai")
    if solved and not solved.get("ok"):
        issues.append(f"Người giải độc lập chọn {json.dumps(solved.get('ai'), ensure_ascii=False)} thay vì đáp án đã soạn "
                      f"({solved.get('ly_do', '')}); hãy làm đáp án đúng thật sự duy nhất.")
    if card.get("tu_ngoai_cap"):
        issues.append("Thay các chữ/từ vượt cấp: " + "、".join(card["tu_ngoai_cap"]))
    return issues


def _fix_round(job: dict, vocab: set[str], mutex: threading.Lock) -> int:
    targets = [c for c in job["the"] if not c.get("duyet") and _problems(c)]
    by_part: dict[int, list[dict]] = {}
    for c in targets:
        by_part.setdefault(c["phan"], []).append(c)

    def work(phan_cards):
        phan, cards = phan_cards
        for start in range(0, len(cards), 5):
            group = cards[start:start + 5]
            message = "Sửa các mục sau cho hết lỗi, giữ nguyên kiểu câu:\n" + "\n".join(
                f"Mục {i}: " + "; ".join(_problems(c)) for i, c in enumerate(group, start=1))
            db = SessionLocal()
            try:
                body = SimpleNamespace(cap_do_id=job["cap_do_id"], phan=phan, muc=[c["muc"] for c in group],
                                       tin_nhan=message, lich_su=[])
                try:
                    changes = parts_svc.chat_part(db, body)["sua"]
                except AiDraftError:
                    changes = []
            finally:
                db.close()
            for change in changes:
                card = group[change["stt"] - 1]
                fresh = json.loads(json.dumps(card))
                _replace_content(fresh, change["the"])
                _check_content(fresh, vocab, job["cap"])
                with mutex:  # thay nguyên mục trong khóa: luồng khác đang ghi tệp không thấy mục sửa dở
                    card.clear()
                    card.update(fresh)
                    _write(job)

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(work, by_part.items()))
    return len(targets)


def _run(job_id: str) -> None:
    mutex = threading.Lock()
    try:
        with _lock(job_id):
            job = _read(job_id)
        level = job["level"]
        _progress(job, 0)
        _generate(job, mutex)
        expected_total = sum(p["so_cau"] for p in BLUEPRINT[level]["phan"])
        have_total = sum(c["so_cau"] for c in job["the"])
        if have_total < expected_total:
            raise AiDraftError(
                f"Đã soạn {have_total}/{expected_total} câu theo cấu trúc {job['cap']} (do giới hạn lượt gọi AI/phút). "
                "Bấm “Chạy tiếp” để AI soạn nốt các câu còn thiếu đúng chuẩn cấu trúc.",
                502,
            )

        _progress(job, 1)
        db = SessionLocal()
        try:
            vocab = checks.load_vocabulary(db, job["cap_do_id"])
        finally:
            db.close()
        pending = [c for c in job["the"] if c.get("giai_lai") is None and not c.get("duyet")]
        with ThreadPoolExecutor(max_workers=4 if is_real_openai_endpoint() else 2) as pool:
            list(pool.map(lambda c: _check_content(c, vocab, job["cap"]), pending))
        _write(job)

        for round_no in range(job.get("vong_sua", 0), FIX_ROUNDS):
            _progress(job, 2, f"Vòng {round_no + 1}/{FIX_ROUNDS}")
            fixed = _fix_round(job, vocab, mutex)
            job["vong_sua"] = round_no + 1
            _write(job)
            if not fixed:
                break

        for step, kind in ((3, "hinh"), (4, "audio")):
            todo = [c for c in job["the"] if any(s["loai"] == kind and not _get(c["muc"], s["path"]) for s in slots(c["muc"]))]
            if kind == "hinh" and todo:
                img_descs = [
                    s["nguon"] for c in todo for s in slots(c["muc"])
                    if s["loai"] == "hinh" and not _get(c["muc"], s["path"]) and s.get("nguon")
                ]
                translate_scenes_batch(img_descs)
            done = [0]

            def work(card, kind=kind, step=step, todo=todo, done=done):
                fresh = json.loads(json.dumps(card))
                _fill_media(fresh, level, kind)
                with mutex:
                    card.clear()
                    card.update(fresh)
                    done[0] += 1
                    _progress(job, step, f"{done[0]}/{len(todo)} mục")

            _progress(job, step, f"0/{len(todo)} mục")
            media_workers = 3 if kind == "audio" else 2
            with ThreadPoolExecutor(max_workers=media_workers) as pool:
                list(pool.map(work, todo))

        _progress(job, 5)
        _assemble(job)
        job["trang_thai"] = "cho_duyet"
        job["buoc"] = None
        job["loi"] = None
        _write(job)
    except Exception as error:  # ghi lỗi để Giảng viên bấm "Chạy tiếp"; không để phiên kẹt ở "đang chạy"
        message = getattr(error, "message", None) or "Có lỗi khi soạn đề, bấm Chạy tiếp để làm tiếp phần còn dở"
        try:
            with _lock(job_id):
                current = _read(job_id)
                current.update({"trang_thai": "loi", "loi": message})
                _write(current)
        except Exception:
            pass
    finally:
        _RUNNING.discard(job_id)


def _assemble(job: dict, pauses: dict | None = None) -> None:
    """Ghép bài Nghe nếu đủ âm thanh; chưa đủ thì ghi chú, Giảng viên ghép lại sau khi xử lý."""
    level = job["level"]
    listen = [p for p in BLUEPRINT[level]["phan"] if p["ky_nang"] == "nghe"]
    if not listen:
        job["am_thanh"] = None
        return
    if pauses is not None:
        job["nghi"] = {str(k): v for k, v in pauses.items()}
    numbers = numbering(job)
    order = [[{**c["muc"], "so": numbers[c["key"]]} for c in ordered_cards(job, p["phan"])] for p in listen]
    seq = listening_audio.script_for(level, BLUEPRINT[level]["phan"], order,
                                     {int(k): int(v) for k, v in (job.get("nghi") or {}).items()})
    try:
        job["am_thanh"] = {**listening_audio.build(level, seq), "cu": False, "loi": None}
    except AiMediaError as error:
        job["am_thanh"] = {"duong_dan": None, "moc": [], "giay": 0, "cu": True, "loi": error.message}


def _start(job_id: str) -> None:
    with _GLOBAL:
        if job_id in _RUNNING:
            return
        _RUNNING.add(job_id)
    _POOL.submit(_run, job_id)


# ---------------------------------------------------------------- API cho endpoint

def readiness() -> dict:
    return {"ai": ai_ready(), "giong_doc": tts_ready(), "tao_hinh": image_ready(), "nhin_anh": vision_ready(),
            "nghe_lai": stt_ready()}


def create_job(db, cap_do_id: int, chu_de: str | None, yeu_cau: str | None, lecturer_id: int) -> str:
    try:
        level_name, level = parts_svc.resolve_level(db, cap_do_id)
    except AiDraftError as error:
        raise JobError(error.message, error.status_code) from error
    db.rollback()
    if not ai_ready():
        raise JobError("Chưa cấu hình AI (OPENAI_API_KEY, OPENAI_MODEL trong .env)", 503)
    job_id = uuid.uuid4().hex
    _write({
        "id": job_id, "cap_do_id": cap_do_id, "cap": level_name, "level": level, "nguoi_tao_id": lecturer_id,
        "chu_de": chu_de, "yeu_cau": yeu_cau, "trang_thai": "dang_chay", "buoc": None, "the": [], "am_thanh": None,
        "nghi": {}, "vong_sua": 0, "loi": None, "bo_de_id": None,
        "tao_luc": datetime.now().isoformat(timespec="seconds"),
    })
    _start(job_id)
    return job_id


def view(job: dict) -> dict:
    """Dữ liệu trả giao diện: kèm đèn, lý do, số câu, cấu trúc phần, tình trạng chạy."""
    status = job["trang_thai"]
    if status == "dang_chay" and job["id"] not in _RUNNING:
        status = "gian_doan"  # máy chủ khởi động lại giữa chừng
    numbers = numbering(job)
    cards = []
    for c in job["the"]:
        den, red, yellow = light(c)
        cards.append({**c, "so": numbers.get(c["key"]), "den": den, "ly_do_do": red, "ly_do_vang": yellow})
    cards.sort(key=lambda c: c["so"] or 0)
    data = BLUEPRINT[job["level"]]
    return {
        **{k: job[k] for k in ("id", "cap_do_id", "cap", "chu_de", "yeu_cau", "buoc", "loi", "bo_de_id",
                               "tao_luc", "cap_nhat_luc", "am_thanh")},
        "trang_thai": status, "the": cards, "thoi_luong_phut": data["thoi_luong_phut"],
        "phan": [{**p, "nghi": int((job.get("nghi") or {}).get(str(p["phan"]), listening_audio.default_pause(p)))
                  if p["ky_nang"] == "nghe" else None} for p in data["phan"]],
        "dem": {d: sum(1 for c in cards if c["den"] == d) for d in ("do", "vang", "xanh")},
        "san_sang": readiness(),
    }


def get_job(job_id: str, lecturer_id: int) -> dict:
    return view(_owned(job_id, lecturer_id))


def list_jobs(lecturer_id: int) -> list[dict]:
    if not JOB_DIR.is_dir():
        return []
    rows = []
    for path in sorted(JOB_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if job.get("nguoi_tao_id") != lecturer_id:
            continue
        status = job["trang_thai"]
        if status == "dang_chay" and job["id"] not in _RUNNING:
            status = "gian_doan"
        total_need = sum(p["so_cau"] for p in BLUEPRINT.get(job.get("level", 1), BLUEPRINT[1])["phan"])
        have_q = sum(c.get("so_cau", 1) for c in job.get("the", []))
        rows.append({"id": job["id"], "cap": job["cap"], "chu_de": job.get("chu_de"), "trang_thai": status,
                     "tao_luc": job.get("tao_luc"), "so_muc": len(job["the"]), "so_cau": have_q,
                     "tong_cau": total_need, "bo_de_id": job.get("bo_de_id")})
    return rows


def _editable(job: dict) -> None:
    if job["id"] in _RUNNING or job["trang_thai"] == "dang_chay":
        raise JobError("AI đang soạn đề, đợi chạy xong mới sửa được", 409)
    if job["trang_thai"] == "da_duyet":
        raise JobError("Đề đã duyệt; sửa câu trong ngân hàng hoặc trang soạn đề", 409)


def resume(job_id: str, lecturer_id: int) -> None:
    job = _owned(job_id, lecturer_id)
    if job["trang_thai"] == "da_duyet":
        raise JobError("Đề đã duyệt", 409)
    if job["id"] in _RUNNING:
        return
    _mutate(job_id, lambda j: j.update({"trang_thai": "dang_chay", "loi": None}))
    _start(job_id)


def delete_job(job_id: str, lecturer_id: int) -> None:
    job = _owned(job_id, lecturer_id)
    if job["id"] in _RUNNING:
        raise JobError("AI đang soạn đề, đợi chạy xong mới bỏ được", 409)
    _file(job_id).unlink(missing_ok=True)


def _card_snapshot(job_id: str, lecturer_id: int, key: str) -> tuple[dict, dict]:
    job = _owned(job_id, lecturer_id)
    _editable(job)
    card = next((c for c in job["the"] if c["key"] == key), None)
    if card is None:
        raise JobError("Không tìm thấy mục", 404)
    if card.get("duyet"):
        raise JobError("Mục đã lưu vào ngân hàng, sửa ở trang câu hỏi", 409)
    return job, json.loads(json.dumps(card))


def _store_card(job_id: str, card: dict, base_version: int, audio_changed: bool) -> dict:
    def apply(job):
        index = next((i for i, c in enumerate(job["the"]) if c["key"] == card["key"]), None)
        if index is None:
            raise JobError("Mục đã bị bỏ", 409)
        if job["the"][index].get("ban") != base_version:
            raise JobError("Mục vừa được sửa ở nơi khác, tải lại trang rồi làm lại", 409)
        job["the"][index] = card
        if audio_changed and job.get("am_thanh"):
            job["am_thanh"]["cu"] = True  # bài Nghe cần ghép lại
    return view(_mutate(job_id, apply))


def mark(job_id: str, lecturer_id: int, key: str, ok: bool) -> dict:
    _owned(job_id, lecturer_id)

    def apply(job):
        _editable(job)
        card = next((c for c in job["the"] if c["key"] == key), None)
        if card is None:
            raise JobError("Không tìm thấy mục", 404)
        if ok and light(card)[0] == "do":
            raise JobError("Mục còn lỗi chặn (đèn đỏ), xử lý trước khi đánh dấu Đạt", 422)
        card["da_xem"] = ok
    return view(_mutate(job_id, apply))


def mark_green(job_id: str, lecturer_id: int, phan: int | None, tat_ca_hop_le: bool = False) -> dict:
    """Đánh dấu Đạt các mục xanh (hoặc mọi mục không có lỗi chặn đèn đỏ khi tat_ca_hop_le=True)."""
    def apply(job):
        _editable(job)
        allowed = ("xanh", "vang") if tat_ca_hop_le else ("xanh",)
        for card in job["the"]:
            if (phan is None or card["phan"] == phan) and not card.get("duyet") and light(card)[0] in allowed:
                card["da_xem"] = True
    _owned(job_id, lecturer_id)
    return view(_mutate(job_id, apply))


def _level_vocab(job: dict) -> set[str]:
    db = SessionLocal()
    try:
        return checks.load_vocabulary(db, job["cap_do_id"])
    finally:
        db.close()


def _audio_paths(card: dict) -> list:
    return [_get(card["muc"], s["path"]) for s in slots(card["muc"]) if s["loai"] == "audio"]


def ask_fix(db, job_id: str, lecturer_id: int, key: str, message: str) -> dict:
    """Giảng viên nhờ AI sửa một mục; AI sửa, hệ thống kiểm định lại và tạo lại tệp đổi nội dung."""
    job, card = _card_snapshot(job_id, lecturer_id, key)
    base, before = card["ban"], _audio_paths(card)
    body = SimpleNamespace(cap_do_id=job["cap_do_id"], phan=card["phan"], muc=[card["muc"]], tin_nhan=message,
                           lich_su=[SimpleNamespace(**t) for t in card.get("trao_doi", [])[-10:]])
    try:
        result = parts_svc.chat_part(db, body)
    except AiDraftError as error:
        raise JobError(error.message, error.status_code) from error
    card["trao_doi"] = (card.get("trao_doi") or []) + [{"vai_tro": "gv", "noi_dung": message},
                                                        {"vai_tro": "ai", "noi_dung": result["tra_loi"]}]
    if result["sua"]:
        _replace_content(card, result["sua"][0]["the"])
        _check_content(card, _level_vocab(job), job["cap"])
        _fill_media(card, job["level"])
    card["ban"] = base + 1
    return _store_card(job_id, card, base, _audio_paths(card) != before)


def redo(db, job_id: str, lecturer_id: int, key: str) -> dict:
    job, card = _card_snapshot(job_id, lecturer_id, key)
    base = card["ban"]
    others = [checks._texts(c["muc"])[0] for c in job["the"] if c["key"] != key and checks._texts(c["muc"])][:40]
    body = SimpleNamespace(cap_do_id=job["cap_do_id"], phan=card["phan"], kieu=card["muc"]["kieu"], so_muc=1,
                           chu_de=job.get("chu_de"), yeu_cau=job.get("yeu_cau"), tranh=[t[:200] for t in others])
    try:
        fresh = parts_svc.generate_part(db, body)["the"][0]
    except AiDraftError as error:
        raise JobError(error.message, error.status_code) from error
    _replace_content(card, fresh)
    card["kiem_hinh"], card["kiem_am"] = {}, {}
    _check_content(card, _level_vocab(job), job["cap"])
    _fill_media(card, job["level"])
    card["ban"] = base + 1
    return _store_card(job_id, card, base, True)


def remake_file(job_id: str, lecturer_id: int, key: str, path: list) -> dict:
    job, card = _card_snapshot(job_id, lecturer_id, key)
    slot = next((s for s in slots(card["muc"]) if s["path"] == path), None)
    if slot is None:
        raise JobError("Ô tệp không hợp lệ", 422)
    base = card["ban"]
    _set(card["muc"], path, None)
    _make_slot(card, slot, job["level"])
    if not _get(card["muc"], path):
        raise JobError("Chưa tạo được tệp, vui lòng thử lại", 502)
    card.update({"ban": base + 1, "da_xem": False})
    return _store_card(job_id, card, base, slot["loai"] == "audio")


def attach_file(job_id: str, lecturer_id: int, key: str, path: list, file_path: str) -> dict:
    """Gắn tệp Giảng viên tự tải lên (qua /giang-vien/tep) vào một ô; kiểm tự động lại."""
    job, card = _card_snapshot(job_id, lecturer_id, key)
    slot = next((s for s in slots(card["muc"]) if s["path"] == path), None)
    if slot is None:
        raise JobError("Ô tệp không hợp lệ", 422)
    folder = "images/" if slot["loai"] == "hinh" else "audio/"
    if ".." in file_path or not _MEDIA_PATH.fullmatch(file_path) or not file_path.startswith(folder) \
            or not (UPLOADS_DIR / file_path).is_file():
        raise JobError("Tệp không hợp lệ", 422)
    base = card["ban"]
    _set(card["muc"], path, file_path)
    sid = _sid(path)
    if slot["loai"] == "hinh":
        card.setdefault("kiem_hinh", {})[sid] = checks.image_check(file_path, slot["nguon"])
    else:
        card.setdefault("kiem_am", {})[sid] = checks.audio_check(file_path, slot["nguon"])
    card.update({"ban": base + 1, "da_xem": False})
    return _store_card(job_id, card, base, slot["loai"] == "audio")


def reassemble(job_id: str, lecturer_id: int, pauses: dict[int, int]) -> dict:
    job = _owned(job_id, lecturer_id)
    _editable(job)
    _assemble(job, pauses)
    saved = job["am_thanh"]
    return view(_mutate(job_id, lambda j: j.update({"am_thanh": saved, "nghi": job["nghi"]})))


def approve(db, job_id: str, lecturer_id: int, ten: str, ma_de: str, thoi_luong: int | None) -> dict:
    """Duyệt và đăng đề (chặn bấm 2 lần cùng lúc để không tạo trùng câu)."""
    with _GLOBAL:
        if job_id in _APPROVING:
            raise JobError("Đề đang được duyệt, vui lòng đợi", 409)
        _APPROVING.add(job_id)
    try:
        return _approve(db, job_id, lecturer_id, ten, ma_de, thoi_luong)
    finally:
        _APPROVING.discard(job_id)


def _approve(db, job_id: str, lecturer_id: int, ten: str, ma_de: str, thoi_luong: int | None) -> dict:
    """Mọi mục đã Đạt, không đèn đỏ, bài Nghe đã ghép mới."""
    job = _owned(job_id, lecturer_id)
    _editable(job)
    level = job["level"]
    blocked = [c for c in job["the"] if not c.get("duyet") and (light(c)[0] == "do" or not c.get("da_xem"))]
    if blocked:
        raise JobError(f"Còn {len(blocked)} mục chưa được đánh dấu Đạt hoặc còn đèn đỏ", 422)
    listen = any(p["ky_nang"] == "nghe" for p in BLUEPRINT[level]["phan"])
    if listen and (not job.get("am_thanh") or job["am_thanh"].get("cu") or not job["am_thanh"].get("duong_dan")):
        _assemble(job)
        if not job["am_thanh"].get("duong_dan"):
            raise JobError(job["am_thanh"].get("loi") or "Chưa ghép được bài Nghe", 422)
    info = ExamInfoIn(cap_do_id=job["cap_do_id"], ten=ten, ma_de=ma_de, thoi_luong_phut=thoi_luong,
                      nguon="AI soạn theo cấu trúc HSK 2.0, giảng viên kiểm tra và duyệt",
                      tep_audio_chung=(job["am_thanh"] or {}).get("duong_dan") if listen else None)

    groups = parts_svc._groups(db)
    db.rollback()
    # Kiểm tra trước toàn bộ (chưa ghi gì) để không lưu dở dang
    for card in job["the"]:
        if not card.get("duyet"):
            _, _, error = parts_svc.check_item(card["muc"], _part(job, card["phan"]), job["cap_do_id"], groups, level=level)
            if error:
                raise JobError(f"Câu {numbering(job).get(card['key'])}: {error}", 422)

    errors = []
    for card in job["the"]:
        if card.get("duyet"):
            continue
        result = parts_svc.approve_items(db, job["cap_do_id"], _part(job, card["phan"]), groups, [card["muc"]], lecturer_id, level=level)[0]
        if result["loi"]:
            card["loi_duyet"] = result["loi"]
            errors.append(result["loi"])
        else:
            card["duyet"] = {"id": result["id"], "cau_ids": result["cau_ids"]}
            card["loi_duyet"] = None
    saved_cards, saved_audio = job["the"], job["am_thanh"]
    _mutate(job_id, lambda j: j.update({"the": saved_cards, "am_thanh": saved_audio}))
    if errors:
        raise JobError(f"Có {len(errors)} mục chưa lưu được: {errors[0]}", 422)

    items = []
    for part in BLUEPRINT[level]["phan"]:
        for card in ordered_cards(job, part["phan"]):
            items += [ExamItemIn(cau_hoi_id=i, phan=part["phan"]) for i in card["duyet"]["cau_ids"]]
    try:
        exam_id = create_exam(db, info, lecturer_id)
    except (QuestionRuleError, ConflictError) as error:
        raise JobError(error.message, 409 if isinstance(error, ConflictError) else 422) from error
    try:
        set_exam_items(db, exam_id, items)
    except (QuestionRuleError, ConflictError) as error:
        delete_draft_exam(db, exam_id)
        raise JobError(error.message, 422) from error
    published, note = True, None
    try:
        publish_exam(db, exam_id)
    except (QuestionRuleError, ConflictError) as error:
        published, note = False, f"Đã tạo đề nháp nhưng chưa đăng: {error.message}"
    _mutate(job_id, lambda j: j.update({"trang_thai": "da_duyet", "bo_de_id": exam_id}))
    return {"bo_de_id": exam_id, "da_dang": published, "ghi_chu": note}
