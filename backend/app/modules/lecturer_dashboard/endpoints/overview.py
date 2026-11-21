"""Tổng quan Giảng viên: việc cần làm và số liệu nội dung, tính trực tiếp từ CSDL."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.security.require_lecturer import require_lecturer

router = APIRouter()

_LATEST_Q = "c.phien_ban = (SELECT MAX(x.phien_ban) FROM cau_hoi x WHERE x.ma_goc_id = c.ma_goc_id)"
_LATEST_B = "b.phien_ban = (SELECT MAX(x.phien_ban) FROM bo_de x WHERE x.ma_goc_id = b.ma_goc_id)"
_LATEST_T = "t.phien_ban = (SELECT MAX(x.phien_ban) FROM tai_lieu x WHERE x.ma_goc_id = t.ma_goc_id)"


@router.get("/giang-vien/tong-quan")
def overview(db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    uid = lecturer["ma_nguoi_dung"]
    one = lambda sql, **p: int(db.execute(text(sql), p).scalar_one())  # noqa: E731

    todo = {
        "bao_loi_moi": one("SELECT COUNT(*) FROM bao_loi WHERE loai = 'noi_dung' AND nhan_luc IS NULL"),
        "bao_loi_cua_toi": one("SELECT COUNT(*) FROM bao_loi WHERE loai = 'noi_dung' AND nguoi_xu_ly_id = :u AND xu_ly_luc IS NULL", u=uid),
        "cham_sai_cho": one("""SELECT COUNT(*) FROM bao_loi WHERE loai = 'cham_sai'
                               AND (xu_ly_luc IS NULL OR (bs_gui_luc IS NOT NULL AND bs_xu_ly_luc IS NULL))"""),
        "viet_cham_loi": one("""SELECT COUNT(*) FROM cau_tra_loi a
                                WHERE (SELECT k.trang_thai FROM ket_qua_cham k WHERE k.cau_tra_loi_id = a.id ORDER BY k.lan DESC LIMIT 1) = 'loi'"""),
        "cau_hoi_nhap": one(f"SELECT COUNT(*) FROM cau_hoi c WHERE c.cau_cha_id IS NULL AND c.trang_thai = 'nhap' AND {_LATEST_Q}"),
        "de_nhap": one(f"SELECT COUNT(*) FROM bo_de b WHERE b.loai = 'de_thi' AND b.trang_thai = 'nhap' AND {_LATEST_B}"),
        "de_thieu_du_lieu": one(f"""SELECT COUNT(*) FROM bo_de b WHERE b.loai = 'de_thi' AND b.trang_thai = 'nhap' AND {_LATEST_B}
                                    AND (b.thoi_luong_phut IS NULL
                                         OR NOT EXISTS(SELECT 1 FROM bo_de_cau_hoi i WHERE i.bo_de_id = b.id AND i.la_cau_vi_du = 0))"""),
        "bai_nhap": one(f"SELECT COUNT(*) FROM bo_de b WHERE b.loai IN ('thua', 'bai', 'cuoi_thua') AND b.trang_thai = 'nhap' AND {_LATEST_B}"),
        "bai_thieu_cau": one(f"""SELECT COUNT(*) FROM bo_de b WHERE b.loai IN ('bai', 'cuoi_thua') AND b.trang_thai = 'nhap' AND {_LATEST_B}
                                 AND (SELECT COUNT(*) FROM bo_de_cau_hoi i WHERE i.bo_de_id = b.id)
                                     < CASE b.loai WHEN 'bai' THEN 5 ELSE 10 END"""),
        "tai_lieu_nhap": one(f"SELECT COUNT(*) FROM tai_lieu t WHERE t.trang_thai = 'nhap' AND {_LATEST_T}"),
        "tu_vung_nhap": one("SELECT COUNT(*) FROM tu_vung WHERE trang_thai = 'nhap'"),
    }
    totals = {
        "cau_hoi_dang": one("SELECT COUNT(*) FROM cau_hoi WHERE cau_cha_id IS NULL AND trang_thai = 'da_dang'"),
        "de_dang": one("SELECT COUNT(*) FROM bo_de WHERE loai = 'de_thi' AND trang_thai = 'da_dang'"),
        "bai_dang": one("SELECT COUNT(*) FROM bo_de WHERE loai IN ('bai', 'cuoi_thua') AND trang_thai = 'da_dang'"),
        "tu_vung_xuat_ban": one("SELECT COUNT(*) FROM tu_vung WHERE trang_thai = 'xuat_ban'"),
        "tai_lieu_dang": one("SELECT COUNT(*) FROM tai_lieu WHERE trang_thai = 'da_dang'"),
        "cap_do_dang": one("SELECT COUNT(*) FROM cap_do WHERE trang_thai = 'da_dang'"),
    }
    return {"viec_can_lam": todo, "tong_so": totals}
