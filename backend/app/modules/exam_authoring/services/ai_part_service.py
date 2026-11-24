"""Giảng viên soạn đề thi thử MỚI với AI theo từng phần, đúng cấu trúc HSK 2.0.

Luồng: chọn cấp -> chọn phần -> AI soạn nội dung (đúng dạng, đúng số câu, trong phạm vi từ vựng của cấp)
-> AI tự soát lỗi + hệ thống dò trùng ngân hàng -> tạo hình / giọng đọc (ai_media_service, gọi từng tệp)
-> Giảng viên xem, nghe, trao đổi với AI để sửa -> Giảng viên DUYỆT phần (lưu + đăng câu, ghi người duyệt)
-> đủ các phần thì tạo đề nháp (create_exam_from_ai).
- Soạn, soát, trao đổi: không ghi CSDL. Chỉ bước Duyệt mới ghi.
- Đóng giao dịch đọc trước khi gọi AI. AI lỗi thì báo lỗi, không tạo câu giả.
- "muc" = một đơn vị AI soạn: câu đơn, hoặc cụm ngữ liệu (bộ tranh/từ dùng chung + câu con, đoạn + 2 câu hỏi).
"""
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.ai import ai_ready, image_ready, is_real_openai_endpoint, tts_ready
from app.modules.exam_authoring.services.hsk_blueprint import BLUEPRINT, KINDS, find_part, level_number
from app.modules.questions.repositories.question_rows import list_children
from app.modules.questions.schemas.question_payload import QuestionIn
from app.modules.questions.services.ai_draft_service import (
    AiDraftError,
    _ask_json,
    _group_id,
    _groups,
    _groups_hint,
    _str_list,
    _text,
)
from app.modules.questions.services.errors import ConflictError
from app.modules.questions.services.quality_service import find_similar
from app.modules.questions.services.question_rules import QuestionRuleError, validate_question
from app.modules.questions.services.question_status import publish_question
from app.modules.questions.services.save_question import create_question

SYSTEM_PROMPT = (
    "Bạn là chuyên gia ra đề thi HSK 2.0 (汉语水平考试). Bạn soạn câu MỚI hoàn toàn, đúng hình thức đề chính thức "
    "nhưng KHÔNG chép câu của đề thật hay sách đã xuất bản. Chữ Hán giản thể, tự nhiên, đúng ngữ pháp, chỉ dùng từ "
    "trong phạm vi cấp được yêu cầu. Giải thích viết bằng tiếng Việt. Đây là bản nháp để giảng viên duyệt. "
    "Chỉ trả JSON hợp lệ."
)
REVIEW_PROMPT = (
    "Bạn là giám khảo phản biện đề HSK. Soát từng mục và chỉ nêu lỗi THẬT SỰ có, bằng tiếng Việt, ngắn gọn. "
    "Chỉ trả JSON hợp lệ."
)
LISTEN_RULE = ('Lời nghe ("loi_nghe"): mỗi lượt lời một dòng, đầu dòng ghi "男：" hoặc "女："; câu hỏi của người '
               'thứ ba ghi "问："; cấp HSK 1 chỉ 1 người nói 1 câu rồi dòng "问：" hỏi về câu đó.')


def _listen_rule(kieu: str) -> str:
    if kieu in ("nghe_tranh_dung_sai", "nghe_chon_tranh"):
        return 'Lời nghe ("loi_nghe"): chỉ 1 người đọc đúng 1 cụm từ hoặc 1 câu trần thuật ngắn, TUYỆT ĐỐI KHÔNG ghi "男：", "女：" hay "问：".'
    if kieu == "nghe_noi_tranh":
        return 'Lời nghe ("loi_nghe"): hội thoại đúng 2 lượt lời, mỗi lượt 1 dòng bắt đầu bằng "男：" hoặc "女：" (xen kẽ nam/nữ nói trước), KHÔNG có dòng "问：".'
    if kieu == "nghe_phan_doan":
        return ('Lời nghe ("loi_nghe"): dòng đầu là đoạn độc thoại 2–4 câu (không ghi 男/女), dòng thứ hai ghi '
                '"问：<câu nhận định bỏ dấu ★>" để phát thanh viên đọc câu nhận định lên băng như đề HSK 3–4 thật.')
    if kieu == "nghe_doan_2cau":
        return 'Lời nghe ("loi_nghe"): đoạn nói 4–6 câu, cuối lời nghe có đúng 2 dòng "问：" lần lượt đọc 2 câu hỏi.'
    return LISTEN_RULE
COMMON = ('"dich_nghia": "nghĩa tiếng Việt", "giai_thich": "giải thích đáp án (tiếng Việt)", '
          '"nhom_ma": "mã nhóm kiến thức phù hợp hoặc rỗng"')
P_PRINT = '"pinyin": "pinyin của phần chữ IN trên đề"'
P_LISTEN = '"pinyin_nghe": "pinyin của lời nghe"'
CHILD = '"pinyin": "pinyin phần in (nếu có)", "dich_nghia": "...", "giai_thich": "..."'
PER_CALL = {1: 5, 2: 3, 5: 1}  # số mục mỗi lần gọi AI theo kích thước cụm (tránh quá thời gian chờ)

# Dạng câu trong CSDL tương ứng từng kiểu
DANG = {
    "nghe_tranh_dung_sai": "dung_sai", "nghe_phan_doan": "dung_sai", "doc_tranh_tu": "dung_sai",
    "doc_phan_doan": "dung_sai", "nghe_chon_tranh": "chon_mot", "nghe_chon_chu": "chon_mot",
    "doc_doan_chon": "chon_mot", "nghe_noi_tranh": "ngu_lieu", "doc_noi_tranh": "ngu_lieu",
    "doc_ghep_cau": "ngu_lieu", "doc_chon_tu": "ngu_lieu", "nghe_doan_2cau": "ngu_lieu",
    "doc_doan_2cau": "ngu_lieu", "doc_sap_xep_doan": "sap_xep", "viet_sap_xep": "sap_xep",
    "viet_dien_chu": "dien_chu", "viet_tranh": "viet_mo",
}
BOOL_ANSWER = {"nghe_tranh_dung_sai", "nghe_phan_doan", "doc_tranh_tu", "doc_phan_doan"}
SHARED = {"nghe_noi_tranh", "doc_noi_tranh", "doc_ghep_cau", "doc_chon_tu"}  # 6 lựa chọn dùng chung, 5 câu con
PAIR = {"nghe_doan_2cau", "doc_doan_2cau"}  # một đoạn, 2 câu hỏi
IMAGE_OPTIONS = {"nghe_chon_tranh", "nghe_noi_tranh", "doc_noi_tranh"}
MAIN_IMAGE = {"nghe_tranh_dung_sai", "doc_tranh_tu", "viet_tranh"}
PRINTED = {"nghe_phan_doan", "doc_tranh_tu", "doc_phan_doan", "doc_doan_chon", "doc_doan_2cau", "viet_dien_chu"}
PLACEHOLDER = {"tep_hinh": "images/cho_tao.jpg", "tep_audio": "audio/cho_tao.wav"}


def _guide(kieu: str, seg: dict, level: int) -> tuple[str, str]:
    """(mô tả dạng như đề thật, khuôn JSON một mục)."""
    n = seg.get("so_lua_chon") or 3
    img = '{"mo_ta_hinh": "mô tả bức ảnh bằng tiếng Việt: người/vật/hành động cụ thể"}'
    txt = '{"noi_dung": "..."}'
    if kieu == "nghe_tranh_dung_sai":
        unit = "một cụm từ 2–4 chữ" if level == 1 else "một câu ngắn"
        return (f"Mỗi câu: đọc {unit}; trên đề có 1 bức ảnh. Khoảng một nửa số câu ảnh KHỚP lời nghe (dap_an=true), "
                "còn lại ảnh cùng chủ đề nhưng KHÁC (dap_an=false).",
                f'"loi_nghe": "...", "mo_ta_hinh": "...", "dap_an": true, {P_LISTEN}, {COMMON}')
    if kieu == "nghe_chon_tranh":
        return (f"Mỗi câu: đọc một câu; trên đề có {n} ảnh, chỉ 1 ảnh khớp, các ảnh còn lại cùng chủ đề nhưng khác rõ.",
                f'"loi_nghe": "...", "lua_chon": [{", ".join([img] * n)}], "dap_an": 1, {P_LISTEN}, {COMMON}')
    if kieu in ("nghe_noi_tranh", "doc_noi_tranh"):
        what = ("5 hội thoại ngắn 2 lượt lời 男/女" if kieu == "nghe_noi_tranh" else "5 câu ngắn in trên đề")
        field = '"loi_nghe": "男：...\\n女：..."' if kieu == "nghe_noi_tranh" else '"noi_dung": "..."'
        pin = '"pinyin_nghe": "..."' if kieu == "nghe_noi_tranh" else '"pinyin": "..."'
        return (f"Mỗi mục là một cụm: 6 ảnh A–F dùng chung và {what}. Mỗi câu khớp đúng 1 ảnh; 5 câu dùng 5 ảnh "
                "khác nhau, thừa 1 ảnh. Các ảnh phải khác nhau rõ ràng.",
                f'"lua_chon": [{", ".join([img] * 6)}], "cau": [{{{field}, "dap_an": 1, {pin}, '
                f'"dich_nghia": "...", "giai_thich": "..."}} ... đủ 5 câu], "nhom_ma": ""')
    if kieu == "nghe_chon_chu":
        if level == 1:
            talk = "một người nói một câu, rồi dòng 问： hỏi về câu đó"
        elif seg.get("dai"):
            talk = "hội thoại 4–5 lượt lời 男/女 xen kẽ, rồi dòng 问："
        else:
            talk = "hội thoại 2 lượt lời 男/女, rồi dòng 问：" if level < 4 else "hội thoại 2 lượt lời, rồi dòng 问："
        return (f"Mỗi câu: {talk}. Trên đề CHỈ in {n} phương án chữ ngắn; câu hỏi không in.",
                f'"loi_nghe": "...", "lua_chon": [{", ".join([txt] * n)}], "dap_an": 1, {P_LISTEN}, {COMMON}')
    if kieu == "nghe_phan_doan":
        return ("Mỗi câu: một người nói một đoạn 2–4 câu; trên đề in một câu nhận định bắt đầu bằng ★. "
                "Khoảng một nửa đúng, một nửa sai.",
                f'"loi_nghe": "...", "noi_dung": "★ ...", "dap_an": true, {P_PRINT}, {P_LISTEN}, {COMMON}')
    if kieu == "nghe_doan_2cau":
        return ("Mỗi mục: một đoạn nói hoặc hội thoại 5–8 câu, cuối lời nghe có 2 dòng 问： lần lượt hỏi 2 câu. "
                "Mỗi câu hỏi có 4 phương án chữ in trên đề.",
                f'"loi_nghe": "...\\n问：câu 1\\n问：câu 2", "cau": [{{"loi_nghe": "câu hỏi 1", "lua_chon": '
                f'[{", ".join([txt] * 4)}], "dap_an": 1, "giai_thich": "..."}}, {{... câu 2}}], {P_LISTEN}, '
                '"dich_nghia": "...", "nhom_ma": ""')
    if kieu == "doc_tranh_tu":
        return ("Mỗi câu: in 1 từ (kèm pinyin) và 1 ảnh; khoảng một nửa ảnh khớp từ (dap_an=true), còn lại không khớp.",
                f'"noi_dung": "từ", "mo_ta_hinh": "...", "dap_an": true, {P_PRINT}, {COMMON}')
    if kieu == "doc_ghep_cau":
        return ("Mỗi mục là một cụm: 6 câu A–F (câu trả lời / câu tiếp nối) dùng chung và 5 câu hỏi/câu cho sẵn; "
                "mỗi câu ghép đúng 1 lựa chọn, 5 câu dùng 5 lựa chọn khác nhau, thừa 1.",
                f'"lua_chon": [{", ".join([txt] * 6)}], "cau": [{{"noi_dung": "...", "dap_an": 1, {CHILD}}} ... đủ 5 câu], '
                '"nhom_ma": ""')
    if kieu == "doc_chon_tu":
        return ("Mỗi mục là một cụm: 6 từ A–F dùng chung và 5 câu có chỗ trống （  ）; mỗi câu điền đúng 1 từ, "
                "5 câu dùng 5 từ khác nhau, thừa 1 từ. Có thể là hội thoại 2 dòng.",
                f'"lua_chon": [{", ".join([txt] * 6)}], "cau": [{{"noi_dung": "câu có （  ）", "dap_an": 1, {CHILD}}} ... '
                'đủ 5 câu], "nhom_ma": ""')
    if kieu == "doc_phan_doan":
        return ("Mỗi câu: in một đoạn 1–3 câu, dòng sau là câu nhận định bắt đầu bằng ★; xét ★ đúng hay sai theo đoạn. "
                "Khoảng một nửa đúng.",
                f'"noi_dung": "đoạn văn\\n★ ...", "dap_an": true, {P_PRINT}, {COMMON}')
    if kieu == "doc_doan_chon":
        return (f"Mỗi câu: in một đoạn ngắn, dòng sau là câu hỏi bắt đầu bằng ★; {n} phương án chữ.",
                f'"noi_dung": "đoạn văn\\n★ câu hỏi", "lua_chon": [{", ".join([txt] * n)}], "dap_an": 1, {P_PRINT}, {COMMON}')
    if kieu == "doc_doan_2cau":
        return ("Mỗi mục: một đoạn văn 5–8 câu và 2 câu hỏi bắt đầu bằng ★, mỗi câu 4 phương án.",
                f'"noi_dung": "đoạn văn", "cau": [{{"noi_dung": "★ câu hỏi 1", "lua_chon": [{", ".join([txt] * 4)}], '
                f'"dap_an": 1, "giai_thich": "..."}}, {{... câu 2}}], {P_PRINT}, "dich_nghia": "...", "nhom_ma": ""')
    if kieu == "doc_sap_xep_doan":
        return ("Mỗi câu: 3 câu A, B, C đã xáo trộn; sắp đúng thứ tự thành một đoạn mạch lạc (không được đúng sẵn ABC).",
                f'"lua_chon": [{txt}, {txt}, {txt}], "thu_tu_dung": [2, 1, 3], {P_PRINT}, {COMMON}')
    if kieu == "viet_sap_xep":
        return ("Mỗi câu: 3–6 mảnh từ đã xáo trộn; ghép thành một câu đúng ngữ pháp.",
                f'"lua_chon": [{txt}, ...], "cau_dung": ["câu đúng có dấu câu", "cách ghép đúng khác nếu có"], {P_PRINT}, {COMMON}')
    if kieu == "viet_dien_chu":
        return ("Mỗi câu: một câu (có thể là hội thoại) có 1 chỗ trống, trong ngoặc ghi pinyin của chữ cần viết, "
                "ví dụ 没关系，别难（guò）了。 Thí sinh viết 1 chữ Hán.",
                f'"noi_dung": "câu có （pinyin）", "dap_an": ["chữ đúng"], {COMMON}')
    if kieu == "viet_tranh":
        return ("Mỗi câu: 1 ảnh và 1 từ cho sẵn (động từ/tính từ/danh từ cấp 4); thí sinh dùng từ đó viết 1 câu về ảnh.",
                f'"tu_bat_buoc": "từ", "mo_ta_hinh": "...", "tieu_chi": "tiêu chí chấm", "cau_mau": "câu mẫu", {COMMON}')
    raise AiDraftError("Kiểu câu không hỗ trợ", 422)


# ---------------------------------------------------------------- chuẩn hóa mục

def _keep(old: dict | None, key: str, text_key: str, value: str | None, new_obj: dict) -> None:
    """Giữ tệp đã tạo nếu nội dung tạo tệp (mô tả hình / lời nghe) không đổi; đổi thì để trống để tạo lại."""
    path = old.get(key) if isinstance(old, dict) and old.get(text_key) == value else None
    new_obj[key] = path if isinstance(path, str) and path else None


def _answer_int(value, count: int) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= count else None


_OPT_PREFIX_RE = re.compile(r"^\s*[A-Ha-h1-8]\s*[\.\、\)\:：]\s*")


def _options(raw, kind_image: bool, old: list | None, limit: int) -> list[dict]:
    result = []
    items = raw if isinstance(raw, list) else []
    for index, item in enumerate(items[:limit]):
        item = item if isinstance(item, dict) else {"noi_dung": item, "mo_ta_hinh": item}
        prev = old[index] if isinstance(old, list) and index < len(old) and isinstance(old[index], dict) else None
        if kind_image:
            desc = _text(item.get("mo_ta_hinh"), 800)
            option = {"mo_ta_hinh": desc}
            _keep(prev, "tep_hinh", "mo_ta_hinh", desc, option)
        else:
            txt = _text(item.get("noi_dung"), 1000)
            if txt:
                txt = _OPT_PREFIX_RE.sub("", txt).strip() or txt
            option = {"noi_dung": txt}
        result.append(option)
    return result


def normalize(kieu: str, seg: dict, raw: dict, old: dict | None = None) -> dict:
    """Làm sạch một mục AI trả về thành cấu trúc thống nhất cho màn hình duyệt (không tin dữ liệu AI)."""
    old = old if isinstance(old, dict) else {}
    skill = KINDS[kieu][0]
    m: dict = {"kieu": kieu, "nhom_ma": _text(raw.get("nhom_ma"), 50),
               "dich_nghia": _text(raw.get("dich_nghia")), "giai_thich": _text(raw.get("giai_thich"))}
    if skill == "nghe":
        m["loi_nghe"] = _text(raw.get("loi_nghe"))
        m["pinyin_nghe"] = _text(raw.get("pinyin_nghe"))
        if kieu not in SHARED:  # cụm nối tranh: mỗi câu con có âm thanh riêng
            _keep(old, "tep_audio", "loi_nghe", m["loi_nghe"], m)
    if kieu in PRINTED or kieu in ("viet_sap_xep", "doc_sap_xep_doan"):
        m["pinyin"] = _text(raw.get("pinyin"))
    if kieu in PRINTED:
        m["noi_dung"] = _text(raw.get("noi_dung"))
    if kieu in MAIN_IMAGE:
        m["mo_ta_hinh"] = _text(raw.get("mo_ta_hinh"), 800)
        _keep(old, "tep_hinh", "mo_ta_hinh", m["mo_ta_hinh"], m)

    count = 6 if kieu in SHARED else (seg.get("so_lua_chon") or 3)
    if kieu in ("viet_sap_xep",):
        count = 8
    if kieu == "doc_sap_xep_doan":
        count = 3
    if kieu in SHARED or kieu in ("nghe_chon_tranh", "nghe_chon_chu", "doc_doan_chon", "doc_sap_xep_doan", "viet_sap_xep"):
        m["lua_chon"] = _options(raw.get("lua_chon"), kieu in IMAGE_OPTIONS, old.get("lua_chon"), count)

    if kieu in BOOL_ANSWER:
        m["dap_an"] = raw.get("dap_an") if isinstance(raw.get("dap_an"), bool) else None
    elif kieu in ("nghe_chon_tranh", "nghe_chon_chu", "doc_doan_chon"):
        m["dap_an"] = _answer_int(raw.get("dap_an"), len(m["lua_chon"]))
    elif kieu == "doc_sap_xep_doan":
        order = raw.get("thu_tu_dung")
        ok = (isinstance(order, list) and sorted(o for o in order if isinstance(o, int)) == list(range(1, len(m["lua_chon"]) + 1)))
        m["thu_tu_dung"] = order if ok else None
    elif kieu == "viet_sap_xep":
        m["dap_an_chap_nhan"] = _str_list(raw.get("cau_dung") or raw.get("dap_an_chap_nhan"))
    elif kieu == "viet_dien_chu":
        given = raw.get("dap_an") if isinstance(raw.get("dap_an"), (list, str)) else raw.get("dap_an_chap_nhan")
        m["dap_an_chap_nhan"] = _str_list(given, 20)
    elif kieu == "viet_tranh":
        m.update({"tu_bat_buoc": _text(raw.get("tu_bat_buoc"), 20), "tieu_chi": _text(raw.get("tieu_chi")),
                  "cau_mau": _text(raw.get("cau_mau"))})

    if kieu in SHARED or kieu in PAIR:
        size = KINDS[kieu][1]
        old_children = old.get("cau") if isinstance(old.get("cau"), list) else []
        children = []
        for index, c in enumerate((raw.get("cau") if isinstance(raw.get("cau"), list) else [])[:size]):
            c = c if isinstance(c, dict) else {}
            prev = old_children[index] if index < len(old_children) and isinstance(old_children[index], dict) else None
            child = {"giai_thich": _text(c.get("giai_thich")), "dich_nghia": _text(c.get("dich_nghia"))}
            if skill == "nghe":
                child["loi_nghe"] = _text(c.get("loi_nghe"))
                if kieu in SHARED:
                    child["pinyin_nghe"] = _text(c.get("pinyin_nghe"))
                    _keep(prev, "tep_audio", "loi_nghe", child["loi_nghe"], child)
            else:
                child["noi_dung"] = _text(c.get("noi_dung"))
                child["pinyin"] = _text(c.get("pinyin"))
            if kieu in PAIR:
                child["lua_chon"] = _options(c.get("lua_chon"), False, None, 4)
                child["dap_an"] = _answer_int(c.get("dap_an"), len(child["lua_chon"]))
            else:
                child["dap_an"] = _answer_int(c.get("dap_an"), len(m["lua_chon"]))
            children.append(child)
        m["cau"] = children
    if kieu == "nghe_phan_doan":
        stmt = (m.get("noi_dung") or "").lstrip("★☆* ").strip()
        if stmt and m.get("loi_nghe") and stmt not in m["loi_nghe"]:
            m["loi_nghe"] = f"{m['loi_nghe'].rstrip()}\n问：{stmt}"
            _keep(old, "tep_audio", "loi_nghe", m["loi_nghe"], m)
    return m


def shuffle(m: dict) -> dict:
    """Xáo vị trí đáp án đúng (AI hay đặt đáp án ở cùng một vị trí); chỉ dùng khi vừa soạn mới."""
    kieu = m["kieu"]
    if kieu in ("nghe_chon_tranh", "nghe_chon_chu", "doc_doan_chon") and m.get("dap_an"):
        order = list(range(len(m["lua_chon"])))
        random.shuffle(order)
        m["dap_an"] = order.index(m["dap_an"] - 1) + 1
        m["lua_chon"] = [m["lua_chon"][i] for i in order]
    elif kieu in SHARED:
        order = list(range(len(m["lua_chon"])))
        random.shuffle(order)
        m["lua_chon"] = [m["lua_chon"][i] for i in order]
        for child in m["cau"]:
            if child.get("dap_an"):
                child["dap_an"] = order.index(child["dap_an"] - 1) + 1
    elif kieu in PAIR:
        for child in m["cau"]:
            if child.get("dap_an"):
                order = list(range(len(child["lua_chon"])))
                random.shuffle(order)
                child["dap_an"] = order.index(child["dap_an"] - 1) + 1
                child["lua_chon"] = [child["lua_chon"][i] for i in order]
    return m


# ---------------------------------------------------------------- dựng câu hỏi CSDL

def _explain(obj: dict, hide_print_pinyin: bool = False) -> str | None:
    parts = [obj.get("giai_thich")]
    if hide_print_pinyin and obj.get("pinyin"):
        parts.append(f"Pinyin đề bài: {obj['pinyin']}")
    if obj.get("pinyin_nghe"):
        parts.append(f"Pinyin lời nghe: {obj['pinyin_nghe']}")
    if obj.get("cau_mau"):
        parts.append(f"Câu mẫu: {obj['cau_mau']}")
    return "\n".join(p for p in parts if p) or None


def _media(obj: dict, key: str, placeholder: bool) -> str | None:
    value = obj.get(key)
    return value or (PLACEHOLDER[key] if placeholder and key in obj else None)


def _blank(dang: str, cap_do_id: int | None, skill: str | None) -> dict:
    return {
        "dang": dang, "cap_do_id": cap_do_id, "ky_nang": skill, "dung_on_luyen": False, "dung_thi_thu": True,
        "dung_dau_vao": False, "tu_vung_id": None, "nguon_noi_dung": "soan_voi_ai", "nhom_kien_thuc_id": None,
        "noi_dung": None, "tep_audio": None, "tep_hinh": None, "mo_ta_hinh": None, "loi_nghe": None, "pinyin": None,
        "dich_nghia": None, "goi_y": None, "goi_y_2": None, "giai_thich": None, "tu_bat_buoc": None,
        "tieu_chi_mo_ta": None, "diem_toi_da": None, "nguong_dat": None, "dap_an_thu_tu": None,
        "phuong_an": [], "dap_an_chap_nhan": [], "cau_con": [],
    }


def _choice_options(options: list[dict], answer, placeholder: bool) -> list[dict]:
    return [{"noi_dung": o.get("noi_dung"), "tep_hinh": _media(o, "tep_hinh", placeholder),
             "la_dap_an_dung": answer == i} for i, o in enumerate(options, start=1)]


def to_payload(m: dict, cap_do_id: int, groups: list[dict], placeholder: bool = False, level: int = 1) -> dict:
    """Chuyển mục thành dữ liệu câu hỏi chuẩn QuestionIn. Cấp HSK 1–2 giữ Pinyin trên đề; cấp HSK 3–4 ẩn Pinyin trên đề như đề thật."""
    kieu = m["kieu"]
    skill, dang = KINDS[kieu][0], DANG[kieu]
    no_pinyin_on_paper = level >= 3
    q = _blank(dang, cap_do_id, skill)
    q.update({
        "noi_dung": m.get("noi_dung"),
        "pinyin": None if no_pinyin_on_paper else m.get("pinyin"),
        "dich_nghia": m.get("dich_nghia"),
        "giai_thich": _explain(m, hide_print_pinyin=no_pinyin_on_paper),
        "loi_nghe": m.get("loi_nghe"), "mo_ta_hinh": m.get("mo_ta_hinh"),
        "tep_audio": _media(m, "tep_audio", placeholder), "tep_hinh": _media(m, "tep_hinh", placeholder),
    })
    if dang != "ngu_lieu":
        q["nhom_kien_thuc_id"] = _group_id(groups, m.get("nhom_ma"))
    if kieu in BOOL_ANSWER:
        q["phuong_an"] = [{"noi_dung": "Đúng", "tep_hinh": None, "la_dap_an_dung": m.get("dap_an") is True},
                          {"noi_dung": "Sai", "tep_hinh": None, "la_dap_an_dung": m.get("dap_an") is False}]
    elif dang == "chon_mot":
        q["phuong_an"] = _choice_options(m.get("lua_chon") or [], m.get("dap_an"), placeholder)
    elif kieu in SHARED:
        q["phuong_an"] = _choice_options(m.get("lua_chon") or [], None, placeholder)
        for c in m.get("cau") or []:
            child = _blank("chon_bo_chung", None, None)
            child.pop("cau_con")
            child.update({"noi_dung": c.get("noi_dung"), "loi_nghe": c.get("loi_nghe"),
                          "pinyin": None if no_pinyin_on_paper else c.get("pinyin"),
                          "dich_nghia": c.get("dich_nghia"),
                          "giai_thich": _explain(c, hide_print_pinyin=no_pinyin_on_paper),
                          "tep_audio": _media(c, "tep_audio", placeholder), "dap_an_thu_tu": c.get("dap_an")})
            q["cau_con"].append(_child_only(child))
    elif kieu in PAIR:
        for c in m.get("cau") or []:
            child = _blank("chon_mot", None, None)
            # HSK 4 phần Nghe đoạn 2 câu: câu hỏi chỉ đọc trong băng (loi_nghe), trên đề chỉ in 4 phương án A/B/C/D
            printed_stem = None if kieu == "nghe_doan_2cau" else c.get("noi_dung")
            child.update({"noi_dung": printed_stem, "loi_nghe": c.get("loi_nghe"),
                          "giai_thich": _explain(c, hide_print_pinyin=no_pinyin_on_paper),
                          "dich_nghia": c.get("dich_nghia"),
                          "phuong_an": _choice_options(c.get("lua_chon") or [], c.get("dap_an"), False)})
            q["cau_con"].append(_child_only(child))
    elif dang == "sap_xep":
        pieces = [o.get("noi_dung") for o in m.get("lua_chon") or []]
        q["noi_dung"] = "排列顺序。" if kieu == "doc_sap_xep_doan" else "完成句子。"
        q["phuong_an"] = [{"noi_dung": p, "tep_hinh": None, "la_dap_an_dung": False} for p in pieces]
        if kieu == "doc_sap_xep_doan":
            order = m.get("thu_tu_dung") or []
            ok = order and all(p for p in pieces)
            q["dap_an_chap_nhan"] = ["".join(pieces[i - 1] for i in order)] if ok else []
        else:
            q["dap_an_chap_nhan"] = list(m.get("dap_an_chap_nhan") or [])
    elif dang == "dien_chu":
        q["dap_an_chap_nhan"] = list(m.get("dap_an_chap_nhan") or [])
    elif dang == "viet_mo":
        q.update({"noi_dung": "看图，用词造句。", "tu_bat_buoc": m.get("tu_bat_buoc"),
                  "tieu_chi_mo_ta": m.get("tieu_chi"), "diem_toi_da": 10, "nguong_dat": 6})
    return q


def _child_only(child: dict) -> dict:
    """Câu con không mang phân loại / cờ dùng / nguồn (theo câu cha)."""
    for key in ("cap_do_id", "ky_nang", "dung_on_luyen", "dung_thi_thu", "dung_dau_vao", "tu_vung_id",
                "nguon_noi_dung", "nhom_kien_thuc_id", "cau_con"):
        child.pop(key, None)
    return child


def _validate(payload: dict) -> str | None:
    try:
        validate_question(QuestionIn.model_validate(payload))
    except QuestionRuleError as error:
        return error.message
    except ValidationError as error:
        first = error.errors()[0]
        where = ".".join(str(p) for p in first.get("loc", ()))
        return f"Dữ liệu chưa hợp lệ ở {where}: {first.get('msg', '')}"
    return None


def missing_media(m: dict) -> list[str]:
    """Liệt kê tệp còn thiếu (hình / âm thanh) của một mục."""
    missing = []
    if "tep_hinh" in m and not m["tep_hinh"]:
        missing.append("hình của câu")
    if "tep_audio" in m and not m["tep_audio"]:
        missing.append("âm thanh")
    for i, o in enumerate(m.get("lua_chon") or [], start=1):
        if "tep_hinh" in o and not o["tep_hinh"]:
            missing.append(f"hình lựa chọn {chr(64 + i)}")
    for i, c in enumerate(m.get("cau") or [], start=1):
        if "tep_audio" in c and not c["tep_audio"]:
            missing.append(f"âm thanh câu con {i}")
    return missing


def _notes(m: dict, seg: dict) -> list[str]:
    notes = []
    kieu = m["kieu"]
    size = KINDS[kieu][1]
    if size > 1 and len(m.get("cau") or []) != size:
        notes.append(f"Cụm này cần {size} câu con, AI mới soạn {len(m.get('cau') or [])}.")
    if kieu in SHARED:
        answers = [c.get("dap_an") for c in m.get("cau") or [] if c.get("dap_an")]
        if len(answers) != len(set(answers)):
            notes.append("Có hai câu con cùng một đáp án; đề HSK thật mỗi lựa chọn chỉ dùng một lần.")
    if kieu in IMAGE_OPTIONS | MAIN_IMAGE:
        notes.append("Xem kỹ hình có đúng mô tả và khớp đáp án không; hình sai thì bấm Tạo lại hình.")
    if KINDS[kieu][0] == "nghe":
        notes.append("Nghe hết âm thanh, kiểm tra giọng đọc đúng lời nghe và thanh điệu.")
    return notes


def card(m: dict, cap_do_id: int, groups: list[dict], issues: list[str] | None, seg: dict, level: int = 1) -> dict:
    payload = to_payload(m, cap_do_id, groups, placeholder=True, level=level)
    return {"muc": m, "loi": _validate(payload), "van_de_ai": issues, "luu_y": _notes(m, seg),
            "so_cau": KINDS[m["kieu"]][1], "trung_lap": [], "_payload": payload}


def _attach_duplicates(db: Session, cards: list[dict]) -> list[dict]:
    targets = [c for c in cards if c["_payload"].get("noi_dung") and c["_payload"]["dang"] != "ngu_lieu"]
    if targets:
        for c, similar in zip(targets, find_similar(db, [t["_payload"] for t in targets])):
            c["trung_lap"] = similar
    for c in cards:
        c.pop("_payload", None)
    return cards


# ---------------------------------------------------------------- ngữ cảnh

def resolve_level(db: Session, cap_do_id: int) -> tuple[str, int]:
    row = db.execute(text("SELECT ma, ten FROM cap_do WHERE id = :id"), {"id": cap_do_id}).mappings().first()
    if row is None:
        raise AiDraftError("Cấp độ không tồn tại", 422)
    number = level_number(row["ma"], row["ten"])
    if number is None:
        raise AiDraftError("Cấp này chưa có cấu trúc đề HSK 2.0 (hệ thống hỗ trợ HSK 1–4)", 422)
    return str(row["ten"]), number


def _vocabulary(db: Session, cap_do_id: int) -> str:
    """Danh sách từ đã xuất bản từ cấp 1 tới cấp đang soạn (giữ câu trong phạm vi từ vựng)."""
    rows = db.execute(text("""
        SELECT t.chu_han FROM tu_vung t JOIN cap_do c ON c.id = t.cap_do_id
        WHERE t.trang_thai = 'xuat_ban' AND c.thu_tu <= (SELECT thu_tu FROM cap_do WHERE id = :id)
        ORDER BY c.thu_tu, t.id LIMIT 1500"""), {"id": cap_do_id}).scalars().all()
    return "、".join(dict.fromkeys(str(r) for r in rows))


def _part_or_error(level: int, phan: int) -> dict:
    part = find_part(level, phan)
    if part is None:
        raise AiDraftError("Phần thi không có trong cấu trúc đề của cấp này", 422)
    return part


def blueprint_for(db: Session, cap_do_id: int) -> dict:
    name, level = resolve_level(db, cap_do_id)
    db.rollback()
    data = BLUEPRINT[level]
    parts = [{**p, "doan": [{**s, "so_muc": s["so_cau"] // KINDS[s["kieu"]][1]} for s in p["doan"]]} for p in data["phan"]]
    return {"cap": name, "thoi_luong_phut": data["thoi_luong_phut"], "phat_nghe": data["phat_nghe"], "phan": parts,
            "san_sang": {"ai": ai_ready(), "giong_doc": tts_ready(), "tao_hinh": image_ready()}}


# ---------------------------------------------------------------- soát lỗi

def _review_view(m: dict) -> dict:
    def strip(obj):
        if isinstance(obj, dict):
            return {k: strip(v) for k, v in obj.items() if not k.startswith("tep_") and v not in (None, [], "")}
        if isinstance(obj, list):
            return [strip(v) for v in obj]
        return obj
    return strip(m)


def _review(items: list[dict], level_name: str, guide: str) -> list[list[str] | None]:
    if not items:
        return []
    prompt = (
        f"Đề {level_name}. Dạng: {guide}\n"
        "Soát từng mục: (1) đáp án đúng có thật sự duy nhất và đúng không; (2) có phương án gây tranh cãi không; "
        "(3) từ vựng/ngữ pháp có vượt cấp không; (4) mô tả hình có khớp đáp án và đủ khác nhau để chọn không; "
        "(5) lời nghe có đúng định dạng 男/女/问 và tự nhiên không; (6) chữ Hán, pinyin, nghĩa có sai không.\n"
        f"Mục (JSON, đáp án đánh số từ 1): {json.dumps([_review_view(m) for m in items], ensure_ascii=False)}\n"
        'Trả JSON: {"ket_qua": [{"stt": 1, "van_de": ["mô tả lỗi"]}]} — mục không có lỗi để "van_de": [].'
    )
    try:
        data = _ask_json(REVIEW_PROMPT, [{"role": "user", "content": prompt}])
    except AiDraftError:
        return [None] * len(items)
    rows = data.get("ket_qua") if isinstance(data, dict) else None
    result: list[list[str] | None] = [None] * len(items)
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("stt"), int) and 1 <= row["stt"] <= len(items):
                result[row["stt"] - 1] = _str_list(row.get("van_de"), 500, 8)
    return result


# ---------------------------------------------------------------- 1. soạn một phần

def _context(level_name: str, vocab: str, groups: list[dict], chu_de: str | None, yeu_cau: str | None) -> str:
    lines = [f"Cấp: {level_name}."]
    if vocab:
        lines.append(f"Chỉ dùng các từ sau (từ cấp 1 tới cấp này) và từ chức năng thông dụng: {vocab}")
    lines.append(f"Chủ đề: {chu_de or 'đa dạng tình huống đời sống quen thuộc, mỗi mục một tình huống khác'}.")
    if yeu_cau:
        lines.append(f"Yêu cầu thêm của giảng viên: {yeu_cau}")
    hint = _groups_hint(groups)
    if hint:
        lines.append(hint.strip())
    return "\n".join(lines)


def _generate_chunk(kieu: str, seg: dict, level: int, level_name: str, context: str, count: int,
                    part_no: int, chunks: int, avoid: list[str], with_review: bool = True) -> list[tuple[dict, list[str] | None]]:
    guide, shape = _guide(kieu, seg, level)
    listening = f"\n{_listen_rule(kieu)}" if KINDS[kieu][0] == "nghe" else ""
    pinyin_rule = (
        '\nQuy tắc Pinyin đề HSK 1–2: với mọi phương án chữ ("lua_chon"[i]["noi_dung"]), ghi theo mẫu "chữ Hán [pinyin]" '
        '(ví dụ: "商店 [shāngdiàn]", "苹果 [píngguǒ]", KHÔNG ghi chữ cái A/B/C ở đầu); trường "pinyin" ghi đầy đủ thanh điệu.'
        if level <= 2 else
        '\nQuy tắc đề HSK 3–4: KHÔNG ghi pinyin vào trong "noi_dung" hay "lua_chon" (đề HSK 3–4 không in phiên âm).'
    )
    split = f"\nĐây là nhóm {part_no}/{chunks}: chọn tình huống khác các nhóm khác." if chunks > 1 else ""
    avoid_text = ("\nKhông lặp lại các nội dung đã có: " + " | ".join(avoid[:30])) if avoid else ""
    prompt = (
        f"{context}\nSoạn {count} mục cho phần thi: {guide}{listening}{pinyin_rule}{split}{avoid_text}\n"
        f'Trả JSON: {{"muc": [{{ {shape} }}]}} (đúng {count} mục; "dap_an" đánh số từ 1 theo thứ tự lựa chọn)'
    )
    data = _ask_json(SYSTEM_PROMPT, [{"role": "user", "content": prompt}])
    items = data.get("muc") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise AiDraftError("AI trả về dữ liệu không đúng định dạng, vui lòng thử lại", 502)
    muc = [shuffle(normalize(kieu, seg, raw)) for raw in items[:count] if isinstance(raw, dict)]
    reviews = _review(muc, level_name, guide) if with_review else [[] for _ in muc]
    return list(zip(muc, reviews))


def _summary(m: dict) -> str:
    bits = [m.get("noi_dung"), m.get("loi_nghe")]
    bits += [c.get("noi_dung") or c.get("loi_nghe") for c in m.get("cau") or []][:2]
    return " / ".join(b for b in bits if b)[:120]


def generate_part(db: Session, body, with_review: bool = True) -> dict:
    level_name, level = resolve_level(db, body.cap_do_id)
    part = _part_or_error(level, body.phan)
    groups = _groups(db)
    vocab = _vocabulary(db, body.cap_do_id)
    db.rollback()  # không giữ giao dịch khi chờ AI
    segs = part["doan"]
    if body.kieu:  # soạn lại / soạn thêm một đoạn
        segs = [s for s in segs if s["kieu"] == body.kieu]
        if not segs:
            raise AiDraftError("Kiểu câu không thuộc phần này", 422)
    context = _context(level_name, vocab, groups, body.chu_de, body.yeu_cau)
    avoid = [a for a in (body.tranh or []) if a]

    jobs = []
    for seg in segs:
        size = KINDS[seg["kieu"]][1]
        total = body.so_muc if body.kieu and body.so_muc else seg["so_cau"] // size
        per = PER_CALL[size]
        sizes = [per] * (total // per) + ([total % per] if total % per else [])
        jobs += [(seg, n, i + 1, len(sizes)) for i, n in enumerate(sizes)]
    if not jobs:
        raise AiDraftError("Không có mục nào cần soạn", 422)

    cards, failed = [], None
    workers = min(6, len(jobs)) if is_real_openai_endpoint() else min(2, len(jobs))
    with ThreadPoolExecutor(max_workers=workers or 1) as pool:
        futures = [(seg, pool.submit(_generate_chunk, seg["kieu"], seg, level, level_name, context, n, i, k, avoid, with_review))
                   for seg, n, i, k in jobs]
        for seg, future in futures:
            try:
                for m, issues in future.result():
                    cards.append(card(m, body.cap_do_id, groups, issues, seg, level=level))
            except AiDraftError as error:
                failed = error
    if not cards:
        raise failed or AiDraftError("AI không trả về mục nào, vui lòng thử lại", 502)
    _attach_duplicates(db, cards)
    wanted = sum(n for _, n, _, _ in jobs)
    note = "Một phần yêu cầu AI bị lỗi nên số mục ít hơn cần; bấm Soạn thêm để bù." if failed or len(cards) < wanted else None
    return {"the": cards, "ghi_chu": note}


# ---------------------------------------------------------------- 2. trao đổi với AI về một phần

def chat_part(db: Session, body) -> dict:
    level_name, level = resolve_level(db, body.cap_do_id)
    part = _part_or_error(level, body.phan)
    groups = _groups(db)
    db.rollback()
    segs = {s["kieu"]: s for s in part["doan"]}
    current = [m for m in body.muc if isinstance(m, dict) and m.get("kieu") in segs]
    if len(current) != len(body.muc):
        raise AiDraftError("Có mục không thuộc phần này", 422)
    shapes = {k: _guide(k, s, level) for k, s in segs.items()}
    instruction = (
        f"Phần thi {part['ten']} ({part['mo_ta']}), {level_name}.\n"
        + "\n".join(f"- Kiểu {k}: {g} Khuôn JSON: {{ {sh} }}" for k, (g, sh) in shapes.items())
        + (f"\n{LISTEN_RULE}" if part["ky_nang"] == "nghe" else "") + _groups_hint(groups)
        + f"\nCác mục hiện tại (JSON, stt từ 1): "
        + json.dumps([{"stt": i, **_review_view(m)} for i, m in enumerate(current, start=1)], ensure_ascii=False)
        + "\nGiảng viên trao đổi với bạn về phần này. Nếu chỉ hỏi thì trả lời, để sua = []. Nếu cần sửa, trả bản "
        "ĐẦY ĐỦ của từng mục cần sửa theo đúng khuôn JSON của kiểu đó (giữ nguyên kiểu). "
        'Trả JSON: {"tra_loi": "trả lời ngắn cho giảng viên", "sua": [{"stt": 1, "muc": {...}}]}'
    )
    messages = [{"role": "user", "content": instruction}]
    for turn in body.lich_su[-10:]:
        messages.append({"role": "assistant" if turn.vai_tro == "ai" else "user", "content": turn.noi_dung})
    messages.append({"role": "user", "content": body.tin_nhan})
    data = _ask_json(SYSTEM_PROMPT, messages)
    if not isinstance(data, dict):
        raise AiDraftError("AI trả về dữ liệu không đúng định dạng, vui lòng thử lại", 502)

    changes, seen = [], set()
    for row in data.get("sua") or []:
        if not (isinstance(row, dict) and isinstance(row.get("stt"), int) and 1 <= row["stt"] <= len(current)
                and isinstance(row.get("muc"), dict)) or row["stt"] in seen:
            continue
        seen.add(row["stt"])
        old = current[row["stt"] - 1]
        seg = segs[old["kieu"]]
        m = normalize(old["kieu"], seg, row["muc"], old)
        guide = shapes[old["kieu"]][0]
        changes.append({"stt": row["stt"], "the": card(m, body.cap_do_id, groups, _review([m], level_name, guide)[0], seg, level=level)})
    _attach_duplicates(db, [c["the"] for c in changes])
    return {"tra_loi": _text(data.get("tra_loi"), 3000) or "AI không có phản hồi.", "sua": changes}


# ---------------------------------------------------------------- 3. Giảng viên duyệt phần

def _verify_audio(db: Session, ids: list[int]) -> None:
    """Giảng viên đã nghe kiểm tra: đánh dấu âm thanh đã kiểm tra (trigger tự về 0 nếu sau này đổi tệp)."""
    for qid in ids:
        db.execute(text("UPDATE cau_hoi SET da_kiem_tra_audio = 1 WHERE id = :id AND tep_audio IS NOT NULL"), {"id": qid})
    db.commit()


def approve_part(db: Session, body, lecturer_id: int) -> dict:
    """Mỗi mục lưu + đăng trong giao dịch riêng: mục lỗi không chặn mục khác. Trả id câu để ghép đề."""
    _, level = resolve_level(db, body.cap_do_id)
    part = _part_or_error(level, body.phan)
    groups = _groups(db)
    db.rollback()
    return {"ket_qua": approve_items(db, body.cap_do_id, part, groups, body.muc, lecturer_id, level=level)}


def check_item(m, part: dict, cap_do_id: int, groups: list[dict], level: int = 1) -> tuple[dict | None, dict | None, str | None]:
    """Làm sạch lại một mục trước khi lưu; trả (mục, payload, lỗi)."""
    segs = {s["kieu"]: s for s in part["doan"]}
    if not isinstance(m, dict) or m.get("kieu") not in segs:
        return None, None, "Mục không thuộc phần này"
    m = normalize(m["kieu"], segs[m["kieu"]], m, m)  # làm sạch lại, giữ tệp đã tạo
    lack = missing_media(m)
    if lack:
        return m, None, "Còn thiếu " + ", ".join(lack)
    payload = to_payload(m, cap_do_id, groups, level=level)
    error = _validate(payload)
    return m, (None if error else payload), error


def approve_items(db: Session, cap_do_id: int, part: dict, groups: list[dict], items: list, lecturer_id: int, level: int = 1) -> list[dict]:
    results = []
    for index, raw in enumerate(items, start=1):
        _, payload, error = check_item(raw, part, cap_do_id, groups, level=level)
        if error:
            results.append({"stt": index, "id": None, "cau_ids": [], "loi": error})
            continue
        try:
            new_id = create_question(db, QuestionIn.model_validate(payload), lecturer_id)
        except QuestionRuleError as err:
            results.append({"stt": index, "id": None, "cau_ids": [], "loi": err.message})
            continue
        children = [c["id"] for c in list_children(db, new_id)]
        db.rollback()
        try:
            publish_question(db, new_id, lecturer_id)
            _verify_audio(db, [new_id, *children])
        except (QuestionRuleError, ConflictError) as err:
            results.append({"stt": index, "id": new_id, "cau_ids": [], "loi": f"Đã lưu nháp nhưng chưa đăng: {err.message}"})
            continue
        results.append({"stt": index, "id": new_id, "cau_ids": children or [new_id], "loi": None})
    return results
