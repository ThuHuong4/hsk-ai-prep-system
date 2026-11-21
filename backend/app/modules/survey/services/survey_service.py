"""Khảo sát đầu vào (5 câu) — chỉ một lần sau lần đăng nhập đầu tiên.

- Không cập nhật/làm lại; không dùng để xếp trình độ hay khóa/mở cấp.
- Lưu một lần vào các cột ks_* của nguoi_dung (ks_trang_thai để không hiện lại).
- Trả về gợi ý đi thẳng: Thi thử → đề của cấp đã chọn; Ôn luyện/Cả hai → bản đồ kỹ năng đã chọn
  (bắt đầu theo luật mở cấp chung: Nghe/Đọc/Từ vựng từ HSK 1, Viết từ HSK 3).
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, RuleError
from app.modules.practice.services import path_view

SKILL_NAME = {"nghe": "Nghe", "doc": "Đọc", "viet": "Viết", "tu_vung": "Từ vựng"}
SKILL_SLUG = {"nghe": "nghe", "doc": "doc", "viet": "viet", "tu_vung": "tu-vung"}


def _state(db: Session, uid: int) -> str:
    return db.execute(text("SELECT ks_trang_thai FROM nguoi_dung WHERE id = :u"), {"u": uid}).scalar_one()


def get_survey(db: Session, uid: int) -> dict:
    return {"trang_thai": _state(db, uid), "cap_do": [{"id": l["id"], "ten": l["ten"]} for l in path_view.levels(db)]}


def _suggest(db: Session, body, levels: list[dict]) -> dict:
    target = next((l for l in levels if l["id"] == body.cap_muc_tieu_id), None)
    start = "Vì bạn chưa học tiếng Trung" if body.da_hoc == "chua" else "Vì bạn đã học tiếng Trung"
    if body.muc_dich == "thi_thu":
        return {
            "loai": "thi_thu", "tieu_de": f"Thi thử {target['ten']}",
            "ly_do": f"{start} và muốn thi thử {target['ten']}. Làm một đề để làm quen cấu trúc đề và thời gian thi.",
            "duong_dan": f"/hoc-vien/thi-thu/hsk/{target['id']}",
        }
    skill = body.ky_nang
    first = next((l for l in levels if path_view.level_open(l, skill)), None)
    first_name = first["ten"] if first else "cấp đầu"
    extra = f" Bạn có thể vào Thi thử {target['ten']} bất cứ lúc nào." if body.muc_dich == "ca_hai" else ""
    return {
        "loai": "on_luyen", "tieu_de": f"Ôn luyện {SKILL_NAME[skill]} từ {first_name}, thửa 1",
        "ly_do": f"{start} và muốn cải thiện {SKILL_NAME[skill]}. Ôn luyện {SKILL_NAME[skill]} bắt đầu từ {first_name}, "
                 f"có thể làm kiểm tra vượt để đi nhanh hơn.{extra}",
        "duong_dan": f"/hoc-vien/on-luyen/{SKILL_SLUG[skill]}",
    }


def submit_survey(db: Session, uid: int, body) -> dict:
    try:
        state = db.execute(text("SELECT ks_trang_thai FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid}).scalar_one()
        if state != "chua_lam":
            raise ConflictError("Bạn đã làm hoặc bỏ qua khảo sát")
        levels = path_view.levels(db)
        if body.cap_muc_tieu_id not in {l["id"] for l in levels}:
            raise RuleError("Cấp HSK không hợp lệ")
        db.execute(
            text("""UPDATE nguoi_dung SET ks_trang_thai = 'da_tra_loi', ks_da_hoc = :h, ks_cap_muc_tieu_id = :c, ks_muc_dich = :m,
                    ks_ky_nang = :k, ks_phut_moi_ngay = :p, ks_cap_nhat_luc = NOW() WHERE id = :u"""),
            {"h": body.da_hoc, "c": body.cap_muc_tieu_id, "m": body.muc_dich, "k": body.ky_nang, "p": body.phut_moi_ngay, "u": uid},
        )
        db.commit()
        return {"goi_y": _suggest(db, body, levels)}
    except Exception:
        db.rollback()
        raise


def skip_survey(db: Session, uid: int) -> None:
    try:
        db.execute(
            text("UPDATE nguoi_dung SET ks_trang_thai = 'bo_qua', ks_cap_nhat_luc = NOW() WHERE id = :u AND ks_trang_thai = 'chua_lam'"),
            {"u": uid},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
