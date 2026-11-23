import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import { SKILL } from "../../../shared/components/LessonParts.jsx";
import { getNotebook, startNotebookReview } from "../api/notebookApi.js";
import DailyMissions from "../components/DailyMissions.jsx";
import "../styles/notebook.css";

const TABS = [
  { v: "", label: "Tất cả" }, { v: "can_on", label: "Cần ôn" }, { v: "cho_on_lai", label: "Chờ ôn lại" }, { v: "da_cung_co", label: "Đã củng cố" },
];
const STATE = { can_on: "Cần ôn", cho_on_lai: "Chờ ôn lại", da_cung_co: "Đã củng cố" };
const LATIN = /[A-Za-zÀ-ỹ]/;
const fmtDate = (d) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString("vi-VN") : "—");
const today = new Date().toLocaleDateString("en-CA");

// Sổ tay câu sai (mục 5.3): danh sách + ôn tối đa 10 câu, không cần năng lượng
export default function NotebookPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { data, error: loadError, loading } = useRequest((signal) => getNotebook(token, tab, signal), [token, tab]);

  async function review() {
    setBusy(true); setError("");
    try {
      const res = await startNotebookReview(token);
      navigate(`/so-tay/on/${res.luot_id}`);
    } catch (err) {
      setError(err?.message || "Chưa mở được lượt ôn");
      setBusy(false);
    }
  }

  const d = data?.dem;
  const pending = d ? d.can_on + d.cho_on_lai : 0;

  return (
    <section className="xc nb">
      <header className="xc-head">
        <h1>Sổ tay câu sai</h1>
        <p>Câu làm sai hoặc bỏ trống ở bài Ôn luyện, kiểm tra cuối thửa và kiểm tra vượt được tự lưu ở đây. Câu sai Thi thử xem lại trong Lịch sử thi. Ôn Sổ tay không tốn năng lượng.</p>
      </header>

      <div className="nb-top">
        <div className="nb-hero">
          <div className="nb-counts">
            <span><b>{d?.den_han ?? "–"}</b>Đến hạn hôm nay</span>
            <span><b>{d?.can_on ?? "–"}</b>Cần ôn</span>
            <span><b>{d?.cho_on_lai ?? "–"}</b>Chờ ôn lại</span>
            <span><b>{d?.da_cung_co ?? "–"}</b>Đã củng cố</span>
          </div>
          <button type="button" className="xc-btn xc-btn--coral" disabled={busy || !pending} onClick={review}>
            <Icon name="replay" /> {pending ? `Ôn ngay (tối đa ${Math.min(10, pending)} câu)` : "Chưa có câu cần ôn"}
          </button>
          <p className="nb-hint">Đúng lần đầu → Chờ ôn lại (hẹn hôm sau). Đúng khi đến hạn → Đã củng cố, +1 KN. Sai → Cần ôn.</p>
          {error && <p role="alert">{error}</p>}
        </div>
        <DailyMissions compact />
      </div>

      <nav className="nb-tabs" aria-label="Lọc Sổ tay">
        {TABS.map((t) => (
          <button key={t.v} type="button" className={tab === t.v ? "is-on" : ""} aria-pressed={tab === t.v} onClick={() => setTab(t.v)}>{t.label}</button>
        ))}
      </nav>

      {loadError && <p role="alert">{loadError}</p>}
      {loading && <p className="xc-muted">Đang tải...</p>}
      {data && data.cau.length === 0 && (
        <div className="xc-empty"><p>{tab ? "Không có câu nào ở mục này." : "Sổ tay đang trống. Câu làm sai ở Ôn luyện sẽ tự vào đây."}</p></div>
      )}
      {data && data.cau.length > 0 && (
        <ul className="nb-list">
          {data.cau.map((c) => {
            const due = c.trang_thai !== "da_cung_co" && (!c.han_on || c.han_on <= today);
            return (
              <li key={c.cau_hoi_goc_id} className={`nb-item st-${c.trang_thai}`}>
                <div className="nb-item__q">
                  {LATIN.test(c.noi_dung || "") ? <p>{c.noi_dung}</p> : <p className="hz">{c.noi_dung}</p>}
                  {c.pinyin && <small>{c.pinyin}</small>}
                  {c.dich_nghia && <small>{c.dich_nghia}</small>}
                </div>
                <div className="nb-item__a">
                  <span className="nb-label">Đáp án</span>
                  <b className={LATIN.test(c.dap_an || "") ? "" : "hz"}>{c.dap_an || "—"}</b>
                </div>
                <div className="nb-item__meta">
                  <span className={`nb-state st-${c.trang_thai}`}>{STATE[c.trang_thai]}</span>
                  <span>{SKILL[c.ky_nang]} · {c.cap_do}</span>
                  <span>Sai {c.so_lan_sai} lần</span>
                  <span className={due ? "is-due" : ""}>{c.trang_thai === "da_cung_co" ? "Đã củng cố" : due ? "Đến hạn ôn" : `Ôn ngày ${fmtDate(c.han_on)}`}</span>
                  {c.nguon && <span>Từ: {c.nguon}</span>}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
