"""Giảng viên kiểm tra bài Viết mở / Dịch câu do AI chấm (mục 5.2 và 6.4 của nghiệp vụ).

Mỗi lần sửa điểm là một dòng ket_qua_cham mới (lan + 1), không xóa lần cũ; điểm hiện hành
= lần hoan_tat lớn nhất. Kết luận phản ánh ghi vào bao_loi (lần đầu hoặc phần bổ sung bs_*).
Khi sửa điểm câu thuộc bài Ôn luyện / Kiểm tra cuối thửa: tự động đối soát hoàn năng lượng
(giữ cân bằng tuyệt đối với v_doi_soat_nang_luong), cập nhật Sổ tay câu sai và cấp KN / mở khóa ô kế tiếp nếu cả bài đạt.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.practice.services import path_view
from app.modules.questions.repositories.question_rows import find_question, list_options
from app.modules.questions.services.get_question import _shape

_OPEN_REPORT = """(b.xu_ly_luc IS NULL OR (b.bs_gui_luc IS NOT NULL AND b.bs_xu_ly_luc IS NULL))"""

_ATTEMPT_KIND = """
    CASE
      WHEN bd.loai = 'de_thi' THEN 'Thi thử'
      WHEN bd.loai IN ('bai', 'cuoi_thua') THEN 'Ôn luyện'
      WHEN l.loai_boc_cau IS NOT NULL THEN 'Kiểm tra / Sổ tay'
      ELSE 'Khác'
    END
"""


def list_writing(db: Session, tab: str, limit: int, offset: int) -> dict:
    where = ["q.dang IN ('viet_mo', 'dich_cau')", "EXISTS(SELECT 1 FROM ket_qua_cham k0 WHERE k0.cau_tra_loi_id = a.id)"]
    open_report = f"EXISTS(SELECT 1 FROM bao_loi b WHERE b.cau_tra_loi_id = a.id AND b.loai = 'cham_sai' AND {_OPEN_REPORT})"
    reviewed = ("(EXISTS(SELECT 1 FROM ket_qua_cham k1 WHERE k1.cau_tra_loi_id = a.id AND k1.nguon = 'giang_vien') "
                "OR EXISTS(SELECT 1 FROM bao_loi b2 WHERE b2.cau_tra_loi_id = a.id AND b2.loai = 'cham_sai' AND b2.xu_ly_luc IS NOT NULL))")
    if tab == "cho":
        where.append(open_report)
    elif tab == "da":
        where.append(reviewed)
        where.append(f"NOT {open_report}")
    elif tab == "loi":
        where.append("""(SELECT k2.trang_thai FROM ket_qua_cham k2 WHERE k2.cau_tra_loi_id = a.id ORDER BY k2.lan DESC LIMIT 1) = 'loi'""")
    condition = " AND ".join(where)
    base = f"""
        FROM cau_tra_loi a
        JOIN cau_hoi q ON q.id = a.cau_hoi_id
        JOIN luot_lam l ON l.id = a.luot_lam_id
        JOIN nguoi_dung u ON u.id = l.nguoi_dung_id
        LEFT JOIN bo_de bd ON bd.id = l.bo_de_id
        LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
        LEFT JOIN v_ket_qua_hien_hanh k ON k.cau_tra_loi_id = a.id
        LEFT JOIN cap_do cd ON cd.id = COALESCE(q.cap_do_id, p.cap_do_id)
        WHERE {condition}
    """
    total = db.execute(text(f"SELECT COUNT(*) {base}"), {}).scalar_one()
    rows = db.execute(
        text(f"""
            SELECT a.id, u.ho_ten AS hoc_vien, q.ma_goc_id AS ma_cau, LEFT(COALESCE(q.noi_dung, p.noi_dung, ''), 140) AS de_bai,
                   cd.ten AS ten_cap_do, {_ATTEMPT_KIND} AS nguon_luot, LEFT(COALESCE(a.van_ban, ''), 140) AS bai_lam,
                   k.diem, q.diem_toi_da, q.nguong_dat, k.nguon AS nguon_cham, k.tao_luc AS cham_luc,
                   {open_report} AS co_phan_anh_mo,
                   (SELECT k3.trang_thai FROM ket_qua_cham k3 WHERE k3.cau_tra_loi_id = a.id ORDER BY k3.lan DESC LIMIT 1) AS trang_thai_cham_cuoi
            {base}
            ORDER BY {open_report} DESC, COALESCE(k.tao_luc, l.bat_dau_luc) DESC
            LIMIT :limit OFFSET :offset
        """),
        {"limit": limit, "offset": offset},
    ).mappings().all()
    items = []
    for r in rows:
        item = dict(r)
        for key in ("diem", "diem_toi_da", "nguong_dat"):
            if item[key] is not None:
                item[key] = float(item[key])
        item["co_phan_anh_mo"] = bool(item["co_phan_anh_mo"])
        item["dat"] = item["diem"] is not None and item["nguong_dat"] is not None and item["diem"] >= item["nguong_dat"]
        items.append(item)
    return {"tong": int(total), "muc": items}


def _answer(db: Session, cau_tra_loi_id: int, for_update: bool = False) -> dict:
    lock = " FOR UPDATE" if for_update else ""
    row = db.execute(
        text(f"""
            SELECT a.id, a.luot_lam_id, a.cau_hoi_id, a.van_ban, a.xac_nhan_luc, a.phien_ban_luu,
                   a.trang_thai_thao_tac, a.nang_luong_tru, a.nang_luong_hoan,
                   l.nguoi_dung_id, u.ho_ten AS hoc_vien, l.bo_de_id, l.trang_thai AS trang_thai_luot, l.nop_luc
            FROM cau_tra_loi a JOIN luot_lam l ON l.id = a.luot_lam_id JOIN nguoi_dung u ON u.id = l.nguoi_dung_id
            WHERE a.id = :id{lock}
        """),
        {"id": cau_tra_loi_id},
    ).mappings().first()
    if row is None:
        raise NotFoundError()
    return dict(row)


def get_writing_detail(db: Session, cau_tra_loi_id: int) -> dict:
    answer = _answer(db, cau_tra_loi_id)
    question = find_question(db, answer["cau_hoi_id"])
    if question["dang"] not in ("viet_mo", "dich_cau"):
        raise NotFoundError()
    parent = find_question(db, question["cau_cha_id"]) if question["cau_cha_id"] else None
    options = list_options(db, [question["id"]] + ([parent["id"]] if parent else []))
    history = db.execute(
        text("""
            SELECT k.lan, k.nguon, k.trang_thai, k.diem, k.nhan_xet, k.cau_sua, k.ly_do_sua, k.mo_hinh, k.tao_luc,
                   g.ho_ten AS nguoi_cham
            FROM ket_qua_cham k LEFT JOIN nguoi_dung g ON g.id = k.nguoi_cham_id
            WHERE k.cau_tra_loi_id = :id ORDER BY k.lan DESC
        """),
        {"id": cau_tra_loi_id},
    ).mappings().all()
    reports = db.execute(
        text("""
            SELECT b.id, b.ly_do, b.lan_bi_bao, b.tao_luc, b.nhan_luc, b.xu_ly_luc, b.ket_luan, b.phan_hoi, b.lan_ket_qua,
                   b.bs_ly_do, b.bs_gui_luc, b.bs_xu_ly_luc, b.bs_ket_luan, b.bs_phan_hoi, b.bs_lan_ket_qua,
                   x.ho_ten AS nguoi_xu_ly, y.ho_ten AS nguoi_xu_ly_bs, b.nguoi_xu_ly_id
            FROM bao_loi b LEFT JOIN nguoi_dung x ON x.id = b.nguoi_xu_ly_id LEFT JOIN nguoi_dung y ON y.id = b.bs_nguoi_xu_ly_id
            WHERE b.cau_tra_loi_id = :id AND b.loai = 'cham_sai' ORDER BY b.id DESC
        """),
        {"id": cau_tra_loi_id},
    ).mappings().all()
    shaped_history = []
    for h in history:
        item = dict(h)
        item["diem"] = float(item["diem"]) if item["diem"] is not None else None
        shaped_history.append(item)
    current = next((h for h in shaped_history if h["trang_thai"] == "hoan_tat"), None)
    return {
        "id": answer["id"],
        "hoc_vien": answer["hoc_vien"],
        "bai_lam": answer["van_ban"],
        "nop_luc": answer["nop_luc"],
        "cau_hoi": _shape(question, options),
        "ngu_lieu": _shape(parent, options) if parent else None,
        "ket_qua_hien_hanh": current,
        "lich_su": shaped_history,
        "phan_anh": [dict(r) for r in reports],
    }


def _open_report(db: Session, cau_tra_loi_id: int) -> dict | None:
    row = db.execute(
        text(f"""SELECT * FROM bao_loi b WHERE b.cau_tra_loi_id = :id AND b.loai = 'cham_sai' AND {_OPEN_REPORT}
                 ORDER BY b.id DESC LIMIT 1 FOR UPDATE"""),
        {"id": cau_tra_loi_id},
    ).mappings().first()
    return dict(row) if row else None


def claim_report(db: Session, cau_tra_loi_id: int, uid: int) -> None:
    try:
        _answer(db, cau_tra_loi_id, for_update=True)
        report = _open_report(db, cau_tra_loi_id)
        if report is None:
            raise ConflictError("Không có phản ánh đang mở")
        if report["xu_ly_luc"] is None:
            if report["nguoi_xu_ly_id"] and report["nguoi_xu_ly_id"] != uid:
                raise ConflictError("Phản ánh đang do giảng viên khác xử lý")
            db.execute(text("UPDATE bao_loi SET nguoi_xu_ly_id = :u, nhan_luc = COALESCE(nhan_luc, NOW()) WHERE id = :id"),
                       {"u": uid, "id": report["id"]})
        else:
            if report["bs_nguoi_xu_ly_id"] and report["bs_nguoi_xu_ly_id"] != uid:
                raise ConflictError("Yêu cầu bổ sung đang do giảng viên khác xử lý")
            db.execute(text("UPDATE bao_loi SET bs_nguoi_xu_ly_id = :u, bs_nhan_luc = COALESCE(bs_nhan_luc, NOW()) WHERE id = :id"),
                       {"u": uid, "id": report["id"]})
        db.commit()
    except Exception:
        db.rollback()
        raise


def _reconcile_practice_benefits(db: Session, answer: dict, question: dict, new_score: float) -> None:
    """Đồng bộ quyền lợi Học viên khi Giảng viên sửa điểm câu Viết mở / Dịch câu trong bài Ôn luyện:
    - Hoàn năng lượng vào `cau_tra_loi.nang_luong_hoan` + `nguoi_dung.nang_luong` (giữ cân bằng v_doi_soat_nang_luong).
    - Gỡ câu khỏi Sổ tay (`da_loai`) nếu đạt và không còn lần sai nào khác; hoặc đưa vào Sổ tay (`can_on`) nếu bị hạ xuống dưới ngưỡng đạt.
    - Cấp KN lần đầu (`kn_bai` +10 / `kn_cuoi_thua` +20) nếu lượt đã nộp và tất cả các câu trong bài đều đạt.
    """
    if not answer.get("bo_de_id") or answer.get("trang_thai_thao_tac") == "bo_qua":
        return
    lesson = db.execute(
        text("SELECT loai, ma_goc_id FROM bo_de WHERE id = :id"),
        {"id": answer["bo_de_id"]},
    ).mappings().first()
    if not lesson or lesson["loai"] not in ("bai", "cuoi_thua"):
        return

    student_id = int(answer["nguoi_dung_id"])
    root_qid = int(question.get("ma_goc_id") or question["id"])
    threshold = float(question.get("nguong_dat") or 6.0)
    passed_now = float(new_score) >= threshold

    if passed_now:
        can_refund = int(answer.get("nang_luong_tru") or 0) - int(answer.get("nang_luong_hoan") or 0)
        if can_refund > 0:
            cur_energy = int(
                db.execute(text("SELECT nang_luong FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": student_id}).scalar_one()
            )
            max_energy = path_view.max_energy_for_user(db, student_id)
            actual_refund = max(0, min(max_energy - cur_energy, can_refund))
            if actual_refund > 0:
                db.execute(
                    text("""
                        UPDATE cau_tra_loi
                        SET nang_luong_hoan = nang_luong_hoan + :r,
                            hoan_luc = COALESCE(hoan_luc, NOW())
                        WHERE id = :id
                    """),
                    {"r": actual_refund, "id": answer["id"]},
                )
                db.execute(
                    text("UPDATE nguoi_dung SET nang_luong = nang_luong + :r WHERE id = :u"),
                    {"r": actual_refund, "u": student_id},
                )

        still_wrong = db.execute(
            text("""
                SELECT 1
                FROM cau_tra_loi a2
                JOIN luot_lam l2 ON l2.id = a2.luot_lam_id
                JOIN bo_de b2 ON b2.id = l2.bo_de_id AND b2.loai IN ('bai', 'cuoi_thua')
                JOIN cau_hoi q2 ON q2.id = a2.cau_hoi_id
                JOIN v_ket_qua_hien_hanh v2 ON v2.cau_tra_loi_id = a2.id
                WHERE l2.nguoi_dung_id = :u
                  AND COALESCE(q2.ma_goc_id, q2.id) = :g
                  AND a2.trang_thai_thao_tac <> 'bo_qua'
                  AND v2.diem < COALESCE(q2.nguong_dat, 6.0)
                LIMIT 1
            """),
            {"u": student_id, "g": root_qid},
        ).first()
        if still_wrong is None:
            db.execute(
                text("""
                    UPDATE so_tay SET trang_thai = 'da_loai', cap_nhat_luc = NOW()
                    WHERE nguoi_dung_id = :u AND cau_hoi_goc_id = :g AND trang_thai IN ('can_on', 'cho_on_lai')
                """),
                {"u": student_id, "g": root_qid},
            )

        if answer.get("trang_thai_luot") == "da_nop":
            stats = db.execute(
                text("""
                    SELECT COUNT(*) AS tong,
                           SUM(
                             CASE
                               WHEN qx.dang IN ('viet_mo', 'dich_cau') THEN IF(vx.diem >= COALESCE(qx.nguong_dat, 6.0), 1, 0)
                               WHEN vx.diem >= 1 THEN 1
                               ELSE 0
                             END
                           ) AS dat_so
                    FROM cau_tra_loi ax
                    JOIN cau_hoi qx ON qx.id = ax.cau_hoi_id
                    LEFT JOIN v_ket_qua_hien_hanh vx ON vx.cau_tra_loi_id = ax.id
                    WHERE ax.luot_lam_id = :l
                """),
                {"l": answer["luot_lam_id"]},
            ).mappings().one()
            if int(stats["tong"] or 0) > 0 and int(stats["dat_so"] or 0) == int(stats["tong"]):
                reason, amount = ("kn_bai", 10) if lesson["loai"] == "bai" else ("kn_cuoi_thua", 20)
                db.execute(
                    text("""
                        INSERT IGNORE INTO nhat_ky_thuong (nguoi_dung_id, luot_lam_id, ly_do, so_luong, bo_de_goc_id)
                        VALUES (:u, :l, :r, :n, :g)
                    """),
                    {"u": student_id, "l": answer["luot_lam_id"], "r": reason, "n": amount, "g": lesson["ma_goc_id"]},
                )
    else:
        db.execute(
            text("""
                INSERT INTO so_tay (nguoi_dung_id, cau_hoi_goc_id, trang_thai, han_on, cap_nhat_luc)
                VALUES (:u, :g, 'can_on', CURDATE(), NOW())
                ON DUPLICATE KEY UPDATE trang_thai = 'can_on', han_on = CURDATE(), cap_nhat_luc = NOW()
            """),
            {"u": student_id, "g": root_qid},
        )


def decide(db: Session, cau_tra_loi_id: int, body, uid: int) -> None:
    try:
        answer = _answer(db, cau_tra_loi_id, for_update=True)
        question = find_question(db, answer["cau_hoi_id"])
        if question["dang"] not in ("viet_mo", "dich_cau"):
            raise NotFoundError()
        current = db.execute(
            text("SELECT lan FROM v_ket_qua_hien_hanh WHERE cau_tra_loi_id = :id"), {"id": cau_tra_loi_id}
        ).scalar_one_or_none()
        report = _open_report(db, cau_tra_loi_id)

        if body.ket_luan == "sua_diem":
            maximum = float(question["diem_toi_da"])
            if body.diem is None or body.diem < 0 or float(body.diem) > maximum:
                raise RuleError(f"Điểm phải từ 0 đến {maximum:g}")
            if not body.ly_do:
                raise RuleError("Nhập lý do sửa điểm")
            next_lan = int(db.execute(text("SELECT COALESCE(MAX(lan), 0) + 1 FROM ket_qua_cham WHERE cau_tra_loi_id = :id"),
                                      {"id": cau_tra_loi_id}).scalar_one())
            db.execute(
                text("""
                    INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, phien_ban_luu, diem, nhan_xet, ly_do_sua, nguoi_cham_id)
                    VALUES (:id, :lan, 'giang_vien', 'hoan_tat', :pbl, :diem, :nx, :ld, :uid)
                """),
                {"id": cau_tra_loi_id, "lan": next_lan, "pbl": int(answer.get("phien_ban_luu") or 0),
                 "diem": body.diem, "nx": body.nhan_xet, "ld": body.ly_do, "uid": uid},
            )
            _reconcile_practice_benefits(db, answer, question, float(body.diem))
            result_lan = next_lan
        else:
            if report is None:
                raise ConflictError("Không có phản ánh đang mở. Muốn đổi điểm hãy chọn Sửa điểm.")
            if current is None:
                raise ConflictError("Bài chưa có kết quả chấm hoàn tất để giữ nguyên")
            result_lan = current

        if report is not None:
            if report["xu_ly_luc"] is None:
                if report["nguoi_xu_ly_id"] and report["nguoi_xu_ly_id"] != uid:
                    raise ConflictError("Phản ánh đang do giảng viên khác xử lý")
                db.execute(
                    text("""
                        UPDATE bao_loi SET nguoi_xu_ly_id = :u, nhan_luc = COALESCE(nhan_luc, NOW()), xu_ly_luc = NOW(),
                               ket_luan = :kl, phan_hoi = :ph, lan_ket_qua = :lan
                        WHERE id = :id
                    """),
                    {"u": uid, "kl": body.ket_luan, "ph": body.nhan_xet, "lan": result_lan, "id": report["id"]},
                )
            else:
                if report["bs_nguoi_xu_ly_id"] and report["bs_nguoi_xu_ly_id"] != uid:
                    raise ConflictError("Yêu cầu bổ sung đang do giảng viên khác xử lý")
                db.execute(
                    text("""
                        UPDATE bao_loi SET bs_nguoi_xu_ly_id = :u, bs_nhan_luc = COALESCE(bs_nhan_luc, NOW()), bs_xu_ly_luc = NOW(),
                               bs_ket_luan = :kl, bs_phan_hoi = :ph, bs_lan_ket_qua = :lan
                        WHERE id = :id
                    """),
                    {"u": uid, "kl": body.ket_luan, "ph": body.nhan_xet, "lan": result_lan, "id": report["id"]},
                )
        db.commit()
    except Exception:
        db.rollback()
        raise
