import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import "../../exam_catalog/styles/catalog.css";
import { formatDateTime } from "../../../shared/utils/format.js";
import { getMyStats } from "../api/statisticsApi.js";
import ScoreChart from "../components/ScoreChart.jsx";
import "../styles/statistics.css";

// Mục 6.2: thống kê Thi thử của Học viên. Chỉ tính lượt đã chấm xong, tách theo cấp; tính lại mỗi lần mở nên sửa điểm thì cập nhật theo.
const SKILL = { nghe: "Nghe", doc: "Đọc", viet: "Viết" };
const pct = (v) => `${Math.round(v * 100)}%`;

function Delta({ from, to }) {
  const d = Math.round(to - from);
  if (!d) return <span className="st-delta">không đổi</span>;
  return <span className={`st-delta ${d > 0 ? "is-up" : "is-down"}`}>{d > 0 ? `▲ +${d}` : `▼ ${d}`}</span>;
}

export default function StatisticsPage() {
  const { token } = useAuth();
  const { data, error, loading } = useRequest((signal) => getMyStats(token, signal), [token]);
  const [pick, setPick] = useState(null);
  const levels = data?.cap || [];
  const lv = levels.find((l) => l.cap_do_id === (pick ?? data?.cap_gan_nhat)) || levels[0];

  return (
    <section className="xc st">
      <div className="sh-pghead">
        <header className="xc-head">
          <h1>Thống kê thi thử</h1>
          <p>Theo dõi điểm qua từng lượt thi thử. Chỉ tính các lượt đã chấm xong, mỗi cấp xem riêng vì thang điểm khác nhau.</p>
        </header>
        <Link className="xc-btn xc-btn--plain xc-btn--sm" to="/hoc-vien/lich-su-thi">Lịch sử thi thử</Link>
      </div>
      {error && <p role="alert">{error}</p>}
      {loading && <p className="xc-muted">Đang tải...</p>}
      {data?.so_luot_cho_cham > 0 && (
        <p className="st-note">{data.so_luot_cho_cham} lượt còn câu Viết đang chờ chấm, chưa tính vào thống kê.</p>
      )}
      {data && !levels.length && (
        <div className="xc-empty">
          <p>Chưa có lượt thi thử nào chấm xong để thống kê.</p>
          <Link className="xc-btn xc-btn--sm" to="/hoc-vien/thi-thu">Chọn đề thi thử</Link>
        </div>
      )}
      {lv && (
        <>
          {levels.length > 1 && (
            <div className="st-tabs" role="tablist" aria-label="Cấp">
              {levels.map((l) => (
                <button key={l.cap_do_id} type="button" role="tab" aria-selected={l === lv} className={`st-tab${l === lv ? " is-on" : ""}`}
                  onClick={() => setPick(l.cap_do_id)}>{l.cap}</button>
              ))}
            </div>
          )}

          <div className="st-tiles">
            <div className="st-tile"><span>Số lượt thi</span><strong>{lv.so_luot}</strong><small>{lv.cap}</small></div>
            <div className="st-tile"><span>Điểm gần nhất</span><strong>{lv.diem_gan_nhat.toFixed(0)}<small>/{lv.diem_toi_da}</small></strong>
              <small>{formatDateTime(lv.luot[lv.luot.length - 1].nop_luc)}</small></div>
            <div className="st-tile"><span>Điểm cao nhất</span><strong>{lv.diem_cao_nhat.toFixed(0)}<small>/{lv.diem_toi_da}</small></strong>
              <small>Trung bình {lv.diem_trung_binh.toFixed(0)}</small></div>
            <div className="st-tile"><span>Số lượt đạt</span><strong>{lv.so_luot_dat}<small>/{lv.so_luot}</small></strong>
              <small>Mốc đạt {lv.diem_dat} điểm</small></div>
          </div>

          <div className="st-card">
            <h2>Điểm theo từng lượt</h2>
            <ScoreChart key={lv.cap_do_id} attempts={lv.luot} max={lv.diem_toi_da} pass={lv.diem_dat} />
            <details className="st-table">
              <summary>Xem dạng bảng</summary>
              <table>
                <thead><tr><th>Lượt</th><th>Đề</th><th>Nộp lúc</th><th>Điểm</th><th>Kết quả</th></tr></thead>
                <tbody>
                  {lv.luot.map((a, i) => (
                    <tr key={a.id}><td>{i + 1}</td><td><Link to={`/thi-thu/ket-qua/${a.id}`}>{a.ten_de}</Link></td><td>{formatDateTime(a.nop_luc)}</td>
                      <td>{a.tong_diem.toFixed(0)}/{lv.diem_toi_da}</td><td>{a.dat ? "Đạt" : "Chưa đạt"}</td></tr>
                  ))}
                </tbody>
              </table>
            </details>
          </div>

          <div className="st-grid2">
            <div className="st-card">
              <h2>Điểm theo kỹ năng</h2>
              <p className="st-sub">Trung bình các lượt (thang 100 mỗi kỹ năng), so lượt đầu với lượt gần nhất.</p>
              <ul className="st-bars">
                {lv.ky_nang.map((s) => (
                  <li key={s.ky_nang}>
                    <div className="st-bars__row"><span className="st-bars__name">{SKILL[s.ky_nang] || s.ky_nang}</span>
                      <span className="st-bars__val">{s.trung_binh.toFixed(0)}</span></div>
                    <div className="st-meter"><span style={{ width: `${Math.min(100, s.trung_binh)}%` }} /></div>
                    <small>{s.so_luot > 1 ? <>Lượt đầu {s.dau.toFixed(0)} → gần nhất {s.gan_nhat.toFixed(0)} <Delta from={s.dau} to={s.gan_nhat} /></> : "Mới có 1 lượt"}</small>
                  </li>
                ))}
              </ul>
            </div>

            <div className="st-card">
              <h2>Dạng câu cần ôn</h2>
              <p className="st-sub">Cộng dồn mọi lượt của {lv.cap}, xếp từ yếu lên. Dưới 60% câu đúng là cần ôn.</p>
              <ul className="st-types">
                {lv.dang_cau.map((g) => (
                  <li key={`${g.ky_nang}-${g.dang}`} className={g.yeu ? "is-weak" : ""}>
                    <div className="st-types__main">
                      <span className="st-types__name">{g.ten}</span>
                      <small>{g.phan_ten.join(", ")} · đúng {g.dung.toFixed(g.dung % 1 ? 1 : 0)}/{g.tong} câu</small>
                      <div className="st-meter"><span style={{ width: pct(g.ty_le) }} /></div>
                    </div>
                    <span className="st-types__pct">{pct(g.ty_le)}</span>
                    {g.yeu
                      ? <Link className="xc-btn xc-btn--sm" to={`/hoc-vien/on-luyen/${g.ky_nang}?cap=${lv.cap_do_id}`}>⚠ Ôn {SKILL[g.ky_nang]}</Link>
                      : <span className="st-ok">✓ Ổn</span>}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
