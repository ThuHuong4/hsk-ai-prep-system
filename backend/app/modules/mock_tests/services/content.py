"""Đọc nội dung đề thi thử đã đăng để hiển thị cho Học viên (không lộ đáp án khi đang làm)."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.grading import CHOICE_TYPES, correct_option_id, load_set_items as load_items


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
            "dap_an_id": correct_option_id(q, options) if q["dang"] in CHOICE_TYPES else None,
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
