import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { claimReport, listReports, resolveReport } from "../api/lecturerApi.js";
import { DANG_LABELS, SKILL_LABELS, formatDateTime } from "../utils/labels.js";
import "../styles/lecturer.css";

const TABS = [
  { key: "moi", label: "Mới" },
  { key: "dang", label: "Đang xử lý" },
  { key: "xong", label: "Đã xử lý" },
  { key: "tat_ca", label: "Tất cả" },
];
const VERDICT = { da_sua: "Đã sửa", khong_phai_loi: "Không phải lỗi" };

export default function ContentReportsPage() {
  const { token, user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = TABS.some((t) => t.key === params.get("tab")) ? params.get("tab") : "moi";
  const [reloadKey, setReloadKey] = useState(0);
  const { data, error, loading } = useRequest((signal) => listReports(token, { tab }, signal), [token, tab, reloadKey]);
  const [openId, setOpenId] = useState(null);
  const [form, setForm] = useState({ ket_luan: "da_sua", phan_hoi: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  async function run(action) {
    setBusy(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await action();
      setMessage({ type: "ok", text: res.message });
      setReloadKey((k) => k + 1);
      setOpenId(null);
      setForm({ ket_luan: "da_sua", phan_hoi: "" });
    } catch (err) {
      setMessage({ type: "bad", text: err?.message || "Thao tác thất bại" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="lv-page">
      <div className="lv-page__intro">
        <h1>Báo lỗi nội dung</h1>
        <p>Học viên báo lỗi câu, đáp án, lời nghe, ảnh, audio, giải thích. Nhận xử lý → sửa câu (nếu cần) → kết luận và phản hồi. Phản hồi đã gửi không bị ghi đè.</p>
      </div>

      <div className="lv-seg" role="tablist" aria-label="Lọc báo lỗi">
        {TABS.map((t) => (
          <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} className={tab === t.key ? "is-active" : undefined}
            onClick={() => setParams({ tab: t.key })}>{t.label}</button>
        ))}
      </div>

      {message.text && <p role={message.type === "ok" ? "status" : "alert"} className={message.type === "ok" ? "lv-notice" : "lv-alert"}>{message.text}</p>}
      {error && <p role="alert" className="lv-alert">{error}</p>}
      {loading && <p className="lv-muted">Đang tải…</p>}
      {!loading && data?.muc.length === 0 && <p className="lv-card lv-muted">Không có báo lỗi nào trong mục này.</p>}

      <ul className="lv-reports">
        {data?.muc.map((r) => {
          const mine = r.nguoi_xu_ly_id === user.ma_nguoi_dung;
          const closed = Boolean(r.xu_ly_luc);
          return (
            <li key={r.id} className="lv-card">
              <div className="lv-report__head">
                <span className="lv-cell-text">
                  <span className="lv-cell-title">{r.ly_do}</span>
                  <span className="lv-cell-sub">
                    {r.hoc_vien} · {formatDateTime(r.tao_luc)} · Câu #{r.ma_cau} (bản {r.phien_ban}) · {DANG_LABELS[r.dang]} · {SKILL_LABELS[r.ky_nang]} · {r.ten_cap_do}
                  </span>
                  <span className="lv-cell-sub zh">{r.noi_dung_cau}</span>
                </span>
                <span className={`lv-status lv-status--${closed ? "da_dang" : r.nhan_luc ? "da_an" : "moi"}`}>
                  {closed ? VERDICT[r.ket_luan] : r.nhan_luc ? `Đang xử lý${r.nguoi_xu_ly ? ` · ${r.nguoi_xu_ly}` : ""}` : "Mới"}
                </span>
              </div>
              {closed && <p className="lv-result">Phản hồi ({r.nguoi_xu_ly}, {formatDateTime(r.xu_ly_luc)}): {r.phan_hoi}</p>}
              {!closed && (
                <div className="lv-actions">
                  <Link className="xbtn xbtn--ghost xbtn--sm" to={`/giang-vien/cau-hoi/${r.cau_soan_id}`}>Mở câu để sửa</Link>
                  {!r.nhan_luc && <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busy} onClick={() => run(() => claimReport(token, r.id))}>Nhận xử lý</button>}
                  {(!r.nguoi_xu_ly_id || mine) && openId !== r.id && (
                    <button type="button" className="xbtn xbtn--sm" disabled={busy} onClick={() => { setOpenId(r.id); setForm({ ket_luan: "da_sua", phan_hoi: "" }); }}>Kết luận</button>
                  )}
                </div>
              )}
              {openId === r.id && (
                <form className="lv-form" onSubmit={(e) => { e.preventDefault(); run(() => resolveReport(token, r.id, { ket_luan: form.ket_luan, phan_hoi: form.phan_hoi.trim() })); }}>
                  <div className="lv-checks" role="radiogroup" aria-label="Kết luận">
                    <label><input type="radio" name={`kl-${r.id}`} checked={form.ket_luan === "da_sua"} onChange={() => setForm({ ...form, ket_luan: "da_sua" })} /> Đã sửa</label>
                    <label><input type="radio" name={`kl-${r.id}`} checked={form.ket_luan === "khong_phai_loi"} onChange={() => setForm({ ...form, ket_luan: "khong_phai_loi" })} /> Không phải lỗi</label>
                  </div>
                  <div><label htmlFor={`ph-${r.id}`}>Phản hồi cho học viên</label>
                    <textarea id={`ph-${r.id}`} rows={3} required maxLength={3000} value={form.phan_hoi} onChange={(e) => setForm({ ...form, phan_hoi: e.target.value })} /></div>
                  {form.ket_luan === "da_sua" && <p className="lv-help">Nhớ sửa và đăng lại câu trước (sửa câu đã dùng sẽ tạo phiên bản mới).</p>}
                  <div className="lv-actions">
                    <button type="submit" className="xbtn" disabled={busy}>Gửi kết luận</button>
                    <button type="button" className="xbtn xbtn--ghost" onClick={() => setOpenId(null)}>Hủy</button>
                  </div>
                </form>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
