"""Nạp câu hỏi, ngữ liệu cha và phương án dùng chung cho mọi luồng làm bài của Học viên và Khách."""
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.sql_helpers import in_params

QUESTION_FIELDS = (
    "id, ma_goc_id, cau_cha_id, dang, cap_do_id, ky_nang, noi_dung, tep_audio, tep_hinh, mo_ta_hinh, "
    "loi_nghe, pinyin, dich_nghia, goi_y, giai_thich, dap_an_thu_tu, tu_bat_buoc, diem_toi_da, nguong_dat, tu_vung_id"
)


def load_questions_by_ids(db: Session, ids: list[int]) -> tuple[dict[int, dict], dict[int, dict]]:
    """Nạp danh sách câu hỏi (kèm ngữ liệu cha nếu có) và các phương án theo cau_hoi_id."""
    if not ids:
        return {}, {}
    marks, params = in_params("q", ids)
    questions = {
        r["id"]: dict(r)
        for r in db.execute(text(f"SELECT {QUESTION_FIELDS} FROM cau_hoi WHERE id IN ({marks})"), params).mappings().all()
    }
    parent_ids = sorted({q["cau_cha_id"] for q in questions.values() if q["cau_cha_id"] and q["cau_cha_id"] not in questions})
    if parent_ids:
        marks, params = in_params("p", parent_ids)
        for r in db.execute(text(f"SELECT {QUESTION_FIELDS} FROM cau_hoi WHERE id IN ({marks})"), params).mappings().all():
            questions[r["id"]] = dict(r)

    all_ids = list(questions)
    marks, params = in_params("o", all_ids)
    options: dict[int, dict] = {i: {"lua_chon": [], "chap_nhan": []} for i in all_ids}
    for r in db.execute(
        text(f"""
            SELECT id, cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung, tep_hinh
            FROM phuong_an
            WHERE cau_hoi_id IN ({marks})
            ORDER BY cau_hoi_id, vai_tro, thu_tu
        """),
        params,
    ).mappings().all():
        bucket = "lua_chon" if r["vai_tro"] == "lua_chon" else "chap_nhan"
        options[r["cau_hoi_id"]][bucket].append(dict(r))
    return questions, options


def load_set_items(db: Session, bo_de_id: int) -> tuple[list[dict], dict[int, dict], dict[int, dict]]:
    """Nạp danh sách câu theo thứ tự của một bộ đề/bài học, kèm câu hỏi và phương án."""
    items = [
        dict(r)
        for r in db.execute(
            text("SELECT cau_hoi_id, thu_tu, phan, la_cau_vi_du FROM bo_de_cau_hoi WHERE bo_de_id = :id ORDER BY thu_tu"),
            {"id": bo_de_id},
        ).mappings().all()
    ]
    if not items:
        return [], {}, {}
    questions, options = load_questions_by_ids(db, [i["cau_hoi_id"] for i in items])
    number = 0
    for item in items:
        q = questions[item["cau_hoi_id"]]
        owner = questions[q["cau_cha_id"]] if q["cau_cha_id"] else q
        item["ky_nang"] = owner["ky_nang"]
        item["la_cau_vi_du"] = bool(item["la_cau_vi_du"])
        if not item["la_cau_vi_du"]:
            number += 1
            item["so_cau"] = number
        else:
            item["so_cau"] = None
    return items, questions, options


def shuffle_choice_options(q: dict, options: dict, seed: int | None) -> list[dict]:
    """Lấy danh sách phương án hiển thị công khai (ẩn cờ đáp án đúng) và xáo trộn ổn định theo seed."""
    owner_id = q["cau_cha_id"] if q["dang"] == "chon_bo_chung" else q["id"]
    opts = [
        {"id": o["id"], "noi_dung": o["noi_dung"], "tep_hinh": o["tep_hinh"]}
        for o in options[owner_id]["lua_chon"]
    ]
    if q["dang"] != "dung_sai" and seed:
        random.Random(seed).shuffle(opts)
    return opts
