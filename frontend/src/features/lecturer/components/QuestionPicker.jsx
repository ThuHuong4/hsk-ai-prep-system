import { useEffect, useMemo, useState } from "react";

import Icon from "../../../shared/components/Icon.jsx";
import { listQuestions } from "../api/lecturerApi.js";
import { DANG_LABELS, SKILL_LABELS } from "../utils/labels.js";

export default function QuestionPicker({ token, capDoId, kyNang = "", purpose = "thi_thu", chosen, onAdd, title }) {
  const [skill, setSkill] = useState(kyNang);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [state, setState] = useState({ data: null, error: "", loading: true });
  const chosenIds = useMemo(() => new Set(chosen.map((i) => i.cau_cha_id || i.cau_hoi_id)), [chosen]);

  useEffect(() => {
    const controller = new AbortController();
    setState((s) => ({ ...s, loading: true, error: "" }));
    listQuestions(token, { cap_do_id: capDoId, ky_nang: skill, q, trang_thai: "da_dang", dung_thi_thu: purpose === "thi_thu", dung_on_luyen: purpose === "on_luyen", trang: page, so_dong: 10 }, controller.signal)
      .then((data) => setState({ data, error: "", loading: false }))
      .catch((err) => { if (err?.name !== "AbortError") setState({ data: null, error: err?.message || "Không tải được", loading: false }); });
    return () => controller.abort();
  }, [token, capDoId, skill, q, page, purpose]);

  const pages = state.data ? Math.max(1, Math.ceil(state.data.tong / 10)) : 1;
  return (
    <div className="lv-card">
      <h2>{title || "Ngân hàng câu đã đăng"}</h2>
      <div className="lv-filters">
        <select aria-label="Kỹ năng" value={skill} disabled={Boolean(kyNang)} onChange={(e) => { setSkill(e.target.value); setPage(1); }}>
          <option value="">Mọi kỹ năng</option>
          {Object.entries(SKILL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <form className="lv-searchbox" role="search" onSubmit={(e) => { e.preventDefault(); setQ(search.trim()); setPage(1); }}>
          <Icon name="search" />
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm nội dung hoặc mã câu" aria-label="Tìm câu để thêm" />
        </form>
      </div>
      {state.loading && <p className="lv-muted">Đang tải…</p>}
      {state.error && <p role="alert">{state.error}</p>}
      {state.data?.muc.length === 0 && <p className="lv-muted">{`Không có câu đã đăng phù hợp. Đăng câu và bật “Dùng cho ${purpose === "on_luyen" ? "Ôn luyện" : "Thi thử"}” ở mục Ngân hàng câu hỏi trước.`}</p>}
      <ul className="lv-picklist">
        {state.data?.muc.map((row) => (
          <li key={row.id} className="lv-pick">
            <span className="lv-cell-text">
              <span className="lv-cell-sub">
                #{row.ma_goc_id} · {SKILL_LABELS[row.ky_nang]} · {DANG_LABELS[row.dang]}{row.so_cau_con > 0 && ` · ${row.so_cau_con} câu con`}
              </span>
              <span className="zh">{row.tom_tat || "(âm thanh / hình)"}</span>
            </span>
            <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => onAdd(row)} disabled={chosenIds.has(row.id)}>
              {chosenIds.has(row.id) ? "Đã thêm" : <><Icon name="plus" size={16} /> Thêm</>}
            </button>
          </li>
        ))}
      </ul>
      {pages > 1 && (
        <nav className="lv-pager" aria-label="Phân trang ngân hàng câu">
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Trước</button>
          <span>Trang {page}/{pages}</span>
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Sau</button>
        </nav>
      )}
    </div>
  );
}
