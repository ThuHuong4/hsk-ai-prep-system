import { useState } from "react";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { sendReport } from "../api/reportsApi.js";
import "../styles/reports.css";

const KINDS = [
  ["dap_an_sai", "Đáp án sai"],
  ["nhieu_dap_an", "Có nhiều hơn một đáp án đúng"],
  ["de_sai", "Đề bài sai hoặc khó hiểu"],
  ["am_thanh", "Âm thanh lỗi hoặc không khớp"],
  ["hinh_anh", "Hình ảnh lỗi"],
  ["giai_thich", "Giải thích chưa đúng"],
  ["khac", "Lỗi khác"],
];

/**
 * Nút "Báo lỗi câu này" (chỉ hiện sau khi câu đã kiểm tra hoặc bài đã nộp).
 * Báo lỗi đổ về Giảng viên; kết luận và phản hồi xem ở trang Cá nhân.
 */
export default function ReportQuestionButton({ luotId, cauHoiId }) {
  const { token } = useAuth();
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState("dap_an_sai");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [state, setState] = useState({ done: false, message: "", error: "" });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setState({ done: false, message: "", error: "" });
    try {
      const data = await sendReport(token, { luot_lam_id: Number(luotId), cau_hoi_id: cauHoiId, loai_loi: kind, mo_ta: text.trim() });
      setState({ done: true, message: data.message, error: "" });
      setOpen(false);
    } catch (err) {
      const message = err?.message || "Chưa gửi được báo lỗi";
      if (err?.status === 409) setState({ done: true, message, error: "" });
      else setState({ done: false, message: "", error: message });
    } finally {
      setBusy(false);
    }
  }

  if (state.done) return <p className="rq-done" role="status">{state.message}</p>;

  return (
    <div className="rq">
      {!open ? (
        <button type="button" className="rq-open" onClick={() => setOpen(true)}>Báo lỗi câu này</button>
      ) : (
        <form className="rq-form" onSubmit={submit}>
          <label htmlFor={`rq-kind-${cauHoiId}`}>Lỗi gì?</label>
          <select id={`rq-kind-${cauHoiId}`} value={kind} onChange={(e) => setKind(e.target.value)} disabled={busy}>
            {KINDS.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <label htmlFor={`rq-text-${cauHoiId}`}>Mô tả ngắn (ít nhất 5 ký tự)</label>
          <textarea id={`rq-text-${cauHoiId}`} rows={2} minLength={5} maxLength={1000} required value={text} disabled={busy}
            placeholder="Ví dụ: phương án B cũng đúng vì…" onChange={(e) => setText(e.target.value)} />
          {state.error && <p role="alert" className="rq-error">{state.error}</p>}
          <div className="rq-actions">
            <button type="button" className="rq-cancel" onClick={() => setOpen(false)} disabled={busy}>Hủy</button>
            <button type="submit" className="rq-send" disabled={busy || text.trim().length < 5}>{busy ? "Đang gửi…" : "Gửi báo lỗi"}</button>
          </div>
        </form>
      )}
    </div>
  );
}
