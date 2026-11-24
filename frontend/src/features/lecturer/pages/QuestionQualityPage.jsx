import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { getItemQuality } from "../api/lecturerApi.js";
import { useLevels } from "../hooks/useLevels.js";
import { DANG_LABELS, SKILL_LABELS } from "../utils/labels.js";
import "../styles/lecturer.css";

const pct = (v) => `${Math.round(v * 100)}%`;

/**
 * Chất lượng câu hỏi: phân tích câu theo dữ liệu làm bài thật (độ khó, độ phân biệt, phương án sai được chọn nhiều,
 * báo lỗi của học viên). Câu chỉ bị gắn cảnh báo khi đủ số lượt trả lời tối thiểu.
 */
export default function QuestionQualityPage() {
  const { token } = useAuth();
  const levels = useLevels();
  const [filters, setFilters] = useState({ cap_do_id: "", ky_nang: "", chi_canh_bao: true });
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    const params = { chi_canh_bao: filters.chi_canh_bao };
    if (filters.cap_do_id) params.cap_do_id = filters.cap_do_id;
    if (filters.ky_nang) params.ky_nang = filters.ky_nang;
    getItemQuality(token, params, controller.signal)
      .then(setData)
      .catch((err) => err?.name !== "AbortError" && setError(err?.message || "Không tải được dữ liệu"));
    return () => controller.abort();
  }, [token, filters]);

  return (
    <section className="lv-page">
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Chất lượng câu hỏi</h1>
          <p>
            Phân tích từ bài làm thật của học viên: <b>tỉ lệ làm đúng</b> (độ khó), <b>độ phân biệt</b> (nhóm 27% điểm cao
            so với 27% điểm thấp), phương án sai được chọn nhiều nhất và báo lỗi đang chờ. Chỉ cảnh báo khi câu có từ{" "}
            {data?.toi_thieu_luot ?? 10} lượt trả lời.
          </p>
        </div>
      </div>

      <div className="lv-filters">
        <select aria-label="Lọc cấp độ" value={filters.cap_do_id} onChange={(e) => setFilters((f) => ({ ...f, cap_do_id: e.target.value }))}>
          <option value="">Mọi cấp</option>
          {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
        </select>
        <select aria-label="Lọc kỹ năng" value={filters.ky_nang} onChange={(e) => setFilters((f) => ({ ...f, ky_nang: e.target.value }))}>
          <option value="">Mọi kỹ năng</option>
          {Object.entries(SKILL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <label className="lv-inline">
          <input type="checkbox" checked={filters.chi_canh_bao} onChange={(e) => setFilters((f) => ({ ...f, chi_canh_bao: e.target.checked }))} />
          Chỉ câu cần xem lại
        </label>
      </div>

      {error && <p role="alert" className="lv-alert">{error}</p>}
      {!data && !error && <p className="lv-muted">Đang phân tích…</p>}
      {data && data.muc.length === 0 && (
        <p className="lv-muted">
          {filters.chi_canh_bao ? "Chưa có câu nào cần xem lại." : "Chưa có câu nào đủ dữ liệu làm bài."}
        </p>
      )}

      {data && data.muc.length > 0 && (
        <div className="lv-table lv-qa">
          <table>
            <thead>
              <tr>
                <th>Câu</th>
                <th>Lượt</th>
                <th>Làm đúng</th>
                <th>Phân biệt</th>
                <th>Cảnh báo</th>
                <th aria-label="Thao tác" />
              </tr>
            </thead>
            <tbody>
              {data.muc.map((q) => (
                <tr key={q.id} className={q.muc_do >= 3 ? "lv-row--bad" : undefined}>
                  <td>
                    <b>#{q.ma_goc_id}</b> v{q.phien_ban} · {q.ten_cap_do} · {SKILL_LABELS[q.ky_nang]} · {DANG_LABELS[q.dang]}
                    <div className="zh lv-cell-sub">{q.noi_dung}</div>
                    {q.phuong_an_sai_nhieu_nhat && (
                      <small className="lv-muted">
                        Phương án sai chọn nhiều nhất: {q.phuong_an_sai_nhieu_nhat.noi_dung} ({pct(q.phuong_an_sai_nhieu_nhat.ti_le)})
                      </small>
                    )}
                  </td>
                  <td>{q.so_luot}</td>
                  <td>{pct(q.ti_le_dung)}</td>
                  <td>{q.do_phan_biet ?? "—"}</td>
                  <td>
                    {q.canh_bao.length ? (
                      <ul className="lv-flags">{q.canh_bao.map((f) => <li key={f.ma}>{f.mo_ta}</li>)}</ul>
                    ) : (
                      <span className="lv-muted">{q.du_du_lieu ? "Ổn" : "Chưa đủ dữ liệu"}</span>
                    )}
                  </td>
                  <td>
                    <Link className="xbtn xbtn--ghost xbtn--sm" to={`/giang-vien/cau-hoi/${q.cau_soan_id}`}>Xem & sửa</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
