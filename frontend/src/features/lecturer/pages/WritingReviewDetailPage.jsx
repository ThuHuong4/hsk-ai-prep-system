import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { claimWriting, decideWriting, getWriting } from "../api/lecturerApi.js";
import QuestionPreview, { SharedPassage } from "../components/QuestionPreview.jsx";
import { formatDateTime } from "../utils/labels.js";
import "../styles/lecturer.css";

const SOURCE = { ai: "AI", giang_vien: "Giảng viên", code: "Hệ thống" };
const VERDICT = { giu_nguyen: "Giữ nguyên", sua_diem: "Sửa điểm" };

function openReport(reports) {
  return reports.find((r) => !r.xu_ly_luc || (r.bs_gui_luc && !r.bs_xu_ly_luc)) || null;
}

export default function WritingReviewDetailPage() {
  const { id } = useParams();
  const { token, user } = useAuth();
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ ket_luan: "giu_nguyen", diem: "", nhan_xet: "", ly_do: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(() => getWriting(token, id).then((d) => {
    setData(d);
    setForm((f) => ({ ...f, ket_luan: openReport(d.phan_anh) ? "giu_nguyen" : "sua_diem", diem: d.ket_qua_hien_hanh?.diem ?? "" }));
  }), [token, id]);

  useEffect(() => { load().catch((err) => setError(err?.message || "Không tải được bài")); }, [load]);

  async function run(action) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const res = await action();
      setNotice(res.message);
      await load();
      setForm((f) => ({ ...f, nhan_xet: "", ly_do: "" }));
    } catch (err) {
      setError(err?.message || "Thao tác thất bại");
    } finally {
      setBusy(false);
    }
  }

  function submit(event) {
    event.preventDefault();
    const body = { ket_luan: form.ket_luan, nhan_xet: form.nhan_xet.trim(), ly_do: form.ly_do.trim() || null };
    if (form.ket_luan === "sua_diem") body.diem = Number(form.diem);
    run(() => decideWriting(token, id, body));
  }

  if (!data) return error ? <p role="alert" className="lv-alert">{error}</p> : <p className="lv-muted">Đang tải…</p>;

  const report = openReport(data.phan_anh);
  const isSupplement = report && report.xu_ly_luc;
  const claimedByOther = report && !isSupplement && report.nguoi_xu_ly_id && report.nguoi_xu_ly_id !== user.ma_nguoi_dung;
  const current = data.ket_qua_hien_hanh;
  const q = data.cau_hoi;

  return (
    <section className="lv-page">
      <Link to="/giang-vien/cham-viet" className="lv-back"><Icon name="back" size={18} /> Chấm bài Viết</Link>
      <div className="lv-page__intro">
        <h1>Bài Viết của {data.hoc_vien}</h1>
        <p>Nộp lúc {formatDateTime(data.nop_luc) || "—"} · Điểm tối đa {q.diem_toi_da}, ngưỡng đạt {q.nguong_dat}</p>
      </div>

      <div className="lv-editor">
        <div className="lv-editor__form">
          <div className="lv-card">
            <h2>Bài làm</h2>
            <p className="zh lv-answer">{data.bai_lam || "(trống)"}</p>
            {current ? (
              <div className="lv-result">
                <strong>Điểm hiện hành: {current.diem}/{q.diem_toi_da}</strong> · {SOURCE[current.nguon]} · lần {current.lan}
                {current.nhan_xet && <p>{current.nhan_xet}</p>}
                {current.cau_sua && <p className="zh">Câu sửa: {current.cau_sua}</p>}
              </div>
            ) : <p className="lv-alert">Chưa có lần chấm hoàn tất.</p>}
          </div>

          {report && (
            <div className="lv-card lv-card--warn">
              <h2>{isSupplement ? "Yêu cầu xem xét bổ sung" : "Phản ánh chấm sai"}</h2>
              <p>{isSupplement ? report.bs_ly_do : report.ly_do}</p>
              <p className="lv-cell-sub">
                Gửi lúc {formatDateTime(isSupplement ? report.bs_gui_luc : report.tao_luc)}
                {!isSupplement && report.nguoi_xu_ly && ` · đang xử lý: ${report.nguoi_xu_ly}`}
              </p>
              {!isSupplement && !report.nguoi_xu_ly_id && (
                <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busy} onClick={() => run(() => claimWriting(token, id))}>Nhận xử lý</button>
              )}
            </div>
          )}

          <form className="lv-card lv-form" onSubmit={submit}>
            <h2>Kết luận</h2>
            {claimedByOther && <p className="lv-alert">Phản ánh đang do giảng viên khác xử lý.</p>}
            <fieldset className="lv-plain" disabled={busy || claimedByOther}>
              <div className="lv-checks" role="radiogroup" aria-label="Kết luận">
                <label><input type="radio" name="kl" checked={form.ket_luan === "giu_nguyen"} disabled={!report} onChange={() => setForm({ ...form, ket_luan: "giu_nguyen" })} /> Giữ nguyên điểm</label>
                <label><input type="radio" name="kl" checked={form.ket_luan === "sua_diem"} onChange={() => setForm({ ...form, ket_luan: "sua_diem" })} /> Sửa điểm</label>
              </div>
              {!report && <p className="lv-help">Không có phản ánh đang mở; bạn vẫn có thể chủ động sửa điểm (có ghi lý do).</p>}
              {form.ket_luan === "sua_diem" && (
                <div className="lv-grid-3">
                  <div><label htmlFor="wr-diem">Điểm mới (0–{q.diem_toi_da})</label>
                    <input id="wr-diem" type="number" min="0" max={q.diem_toi_da} step="0.25" required value={form.diem} onChange={(e) => setForm({ ...form, diem: e.target.value })} /></div>
                </div>
              )}
              <div><label htmlFor="wr-nx">Nhận xét gửi học viên</label><textarea id="wr-nx" rows={3} required maxLength={3000} value={form.nhan_xet} onChange={(e) => setForm({ ...form, nhan_xet: e.target.value })} /></div>
              {form.ket_luan === "sua_diem" && (
                <div><label htmlFor="wr-ld">Lý do sửa điểm</label><textarea id="wr-ld" rows={2} required maxLength={2000} value={form.ly_do} onChange={(e) => setForm({ ...form, ly_do: e.target.value })} /></div>
              )}
              <div className="lv-actions">
                <button type="submit" className="xbtn" disabled={busy}>{form.ket_luan === "sua_diem" ? "Lưu điểm mới" : "Xác nhận giữ nguyên"}</button>
              </div>
            </fieldset>
            {error && <p role="alert" className="lv-alert">{error}</p>}
            {notice && <p role="status" className="lv-notice">{notice}</p>}
          </form>

          <div className="lv-card">
            <h2>Lịch sử chấm ({data.lich_su.length})</h2>
            <ol className="lv-history">
              {data.lich_su.map((h) => (
                <li key={h.lan}>
                  <strong>Lần {h.lan}</strong> · {SOURCE[h.nguon]}{h.nguoi_cham && ` (${h.nguoi_cham})`} · {formatDateTime(h.tao_luc)} ·{" "}
                  {h.trang_thai === "hoan_tat" ? `${h.diem}/${q.diem_toi_da}` : h.trang_thai === "loi" ? "Lỗi chấm" : "Đang chấm"}
                  {h.nhan_xet && <div className="lv-cell-sub">{h.nhan_xet}</div>}
                  {h.ly_do_sua && <div className="lv-cell-sub">Lý do sửa: {h.ly_do_sua}</div>}
                </li>
              ))}
            </ol>
            {data.phan_anh.some((r) => r.xu_ly_luc) && (
              <>
                <h3>Phản ánh đã xử lý</h3>
                <ul className="lv-history">
                  {data.phan_anh.filter((r) => r.xu_ly_luc).map((r) => (
                    <li key={r.id}>
                      {VERDICT[r.ket_luan]} bởi {r.nguoi_xu_ly} · {formatDateTime(r.xu_ly_luc)}: {r.phan_hoi}
                      {r.bs_xu_ly_luc && <div className="lv-cell-sub">Bổ sung: {VERDICT[r.bs_ket_luan]} bởi {r.nguoi_xu_ly_bs}: {r.bs_phan_hoi}</div>}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </div>

        <aside className="lv-editor__preview" aria-label="Đề bài">
          <h2>Đề bài</h2>
          {data.ngu_lieu && <SharedPassage q={data.ngu_lieu} />}
          <QuestionPreview q={q} />
          {q.tieu_chi_mo_ta && <p className="lv-preview__note">Tiêu chí: {q.tieu_chi_mo_ta}</p>}
        </aside>
      </div>
    </section>
  );
}
