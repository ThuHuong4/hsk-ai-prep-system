"""Đọc nội dung đề thi thử đã đăng để hiển thị cho Học viên (không lộ đáp án khi đang làm)."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.sql_helpers import in_params

_Q_FIELDS = ("id, ma_goc_id, cau_cha_id, dang, cap_do_id, ky_nang, noi_dung, tep_audio, tep_hinh, mo_ta_hinh, "
             "loi_nghe, pinyin, dich_nghia, goi_y, giai_thich, dap_an_thu_tu, tu_bat_buoc, diem_toi_da, nguong_dat, tu_vung_id")


def published_version(db: Session, ma_goc_id: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT b.id, b.ma_goc_id, b.ten, g.ma_de, b.nguon, b.thoi_luong_phut, b.tep_audio_chung, b.cap_do_id,
                   cd.ten AS ten_cap_do, cd.diem_toi_da_thi, cd.diem_dat_thi
            FROM bo_de b JOIN bo_de g ON g.id = b.ma_goc_id JOIN cap_do cd ON cd.id = b.cap_do_id
            WHERE b.ma_goc_id = :g AND b.loai = 'de_thi' AND b.trang_thai = 'da_dang' AND cd.trang_thai = 'da_dang'
            ORDER BY b.phien_ban DESC LIMIT 1
        """),
        {"g": ma_goc_id},
    ).mappings().first()
    return dict(row) if row else None


def exam_version(db: Session, bo_de_id: int) -> dict:
    row = db.execute(
        text("""
            SELECT b.id, b.ma_goc_id, b.ten, g.ma_de, b.nguon, b.thoi_luong_phut, b.tep_audio_chung, b.cap_do_id,
                   cd.ten AS ten_cap_do, cd.diem_toi_da_thi, cd.diem_dat_thi
            FROM bo_de b JOIN bo_de g ON g.id = b.ma_goc_id JOIN cap_do cd ON cd.id = b.cap_do_id
            WHERE b.id = :id
        """),
        {"id": bo_de_id},
    ).mappings().one()
    return dict(row)


def load_items(db: Session, bo_de_id: int) -> tuple[list[dict], dict, dict]:
    """(items theo thứ tự, câu theo id, phương án theo cau_hoi_id). items có ky_nang của câu chủ (câu cha)."""
    items = [dict(r) for r in db.execute(
        text("SELECT cau_hoi_id, thu_tu, phan, la_cau_vi_du FROM bo_de_cau_hoi WHERE bo_de_id = :id ORDER BY thu_tu"),
        {"id": bo_de_id},
    ).mappings().all()]
    ids = [i["cau_hoi_id"] for i in items]
    marks, params = in_params("q", ids)
    questions = {r["id"]: dict(r) for r in db.execute(text(f"SELECT {_Q_FIELDS} FROM cau_hoi WHERE id IN ({marks})"), params).mappings().all()}
    parent_ids = sorted({q["cau_cha_id"] for q in questions.values() if q["cau_cha_id"]})
    if parent_ids:
        marks, params = in_params("p", parent_ids)
        for r in db.execute(text(f"SELECT {_Q_FIELDS} FROM cau_hoi WHERE id IN ({marks})"), params).mappings().all():
            questions[r["id"]] = dict(r)
    all_ids = list(questions)
    marks, params = in_params("o", all_ids)
    options: dict[int, dict] = {i: {"lua_chon": [], "chap_nhan": []} for i in all_ids}
    for r in db.execute(
        text(f"""SELECT id, cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung, tep_hinh
                 FROM phuong_an WHERE cau_hoi_id IN ({marks}) ORDER BY cau_hoi_id, vai_tro, thu_tu"""),
        params,
    ).mappings().all():
        key = "lua_chon" if r["vai_tro"] == "lua_chon" else "chap_nhan"
        options[r["cau_hoi_id"]][key].append(dict(r))
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


def correct_option_id(q: dict, options: dict) -> int | None:
    if q["dang"] == "chon_bo_chung":
        shared = options[q["cau_cha_id"]]["lua_chon"]
        match = next((o for o in shared if o["thu_tu"] == q["dap_an_thu_tu"]), None)
        return match["id"] if match else None
    match = next((o for o in options[q["id"]]["lua_chon"] if o["la_dap_an_dung"]), None)
    return match["id"] if match else None


def _public_option(o: dict) -> dict:
    return {"id": o["id"], "thu_tu": o["thu_tu"], "noi_dung": o["noi_dung"], "tep_hinh": o["tep_hinh"]}


def shape_question(q: dict, options: dict, reveal: bool) -> dict:
    """Câu để hiển thị; reveal=False thì bỏ mọi thông tin đáp án/giải thích/lời nghe."""
    data = {
        "id": q["id"], "dang": q["dang"], "noi_dung": q["noi_dung"], "pinyin": q["pinyin"],
        "tep_hinh": q["tep_hinh"], "tep_audio": q["tep_audio"], "mo_ta_hinh": q["mo_ta_hinh"],
        "tu_bat_buoc": q["tu_bat_buoc"],
        "phuong_an": [_public_option(o) for o in options[q["id"]]["lua_chon"]],
    }
    if q["dang"] == "viet_mo":
        data["diem_toi_da"] = float(q["diem_toi_da"])
    if reveal:
        data.update({
            "loi_nghe": q["loi_nghe"], "dich_nghia": q["dich_nghia"], "giai_thich": q["giai_thich"],
            "dap_an_id": correct_option_id(q, options) if q["dang"] in ("chon_mot", "dung_sai", "chon_bo_chung") else None,
            "dap_an_chap_nhan": [o["noi_dung"] for o in options[q["id"]]["chap_nhan"]],
        })
        if q["dang"] == "viet_mo":
            data["nguong_dat"] = float(q["nguong_dat"])
    return data


def shape_passage(p: dict, options: dict, reveal: bool) -> dict:
    data = {
        "id": p["id"], "noi_dung": p["noi_dung"], "pinyin": p["pinyin"], "tep_hinh": p["tep_hinh"],
        "tep_audio": p["tep_audio"], "mo_ta_hinh": p["mo_ta_hinh"],
        "phuong_an": [_public_option(o) for o in options[p["id"]]["lua_chon"]],
    }
    if reveal:
        data.update({"loi_nghe": p["loi_nghe"], "dich_nghia": p["dich_nghia"], "giai_thich": p["giai_thich"]})
    return data
