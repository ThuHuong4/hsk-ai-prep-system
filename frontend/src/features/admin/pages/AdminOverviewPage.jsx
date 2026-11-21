import { Link } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../lecturer/styles/lecturer.css";
import { getAdminOverview } from "../api/adminApi.js";
import "../styles/admin.css";
import { ACTION_NAME, fmtTime, logText } from "../utils/labels.js";

// Gọn: 4 số chính + 5 thao tác gần nhất
const STATS = [
  { key: "hoc_vien", label: "Học viên", icon: "user", to: "/quan-tri/tai-khoan?vai_tro=1" },
  { key: "giang_vien", label: "Giảng viên", icon: "book", to: "/quan-tri/tai-khoan?vai_tro=3" },
  { key: "khoa", label: "Bị khóa", icon: "lock", to: "/quan-tri/tai-khoan?trang_thai=khoa" },
  { key: "moi_7_ngay", label: "Mới trong 7 ngày", icon: "plus", to: "/quan-tri/tai-khoan" },
];

export default function AdminOverviewPage() {
  const { token } = useAuth();
  const { data, error, loading } = useRequest((signal) => getAdminOverview(token, signal), [token]);

  return (
    <section className="lv-page">
      <div className="lv-page__intro">
        <h1>Tổng quan</h1>
      </div>
      {error && <p role="alert" className="lv-alert">{error}</p>}
      {loading && <p className="lv-muted">Đang tải…</p>}
      {data && (
        <>
          <ul className="lv-stat-grid ad-stats">
            {STATS.map((s) => (
              <li key={s.key}>
                <Link className="lv-stat" to={s.to}>
                  <span className="lv-cell-icon"><Icon name={s.icon} /></span>
                  <span className="lv-stat__num">{data[s.key]}</span>
                  <span className="lv-stat__label">{s.label}</span>
                </Link>
              </li>
            ))}
          </ul>
          <div className="lv-page__head">
            <h2>Thao tác gần đây</h2>
            <Link className="xbtn xbtn--ghost xbtn--sm" to="/quan-tri/nhat-ky">Xem nhật ký</Link>
          </div>
          <div className="lv-table">
            {data.nhat_ky_gan_day.length === 0 && <p className="lv-empty">Chưa có thao tác quản trị nào.</p>}
            {data.nhat_ky_gan_day.map((r) => (
              <div className="lv-tr ad-recent" key={r.id}>
                <span className="lv-cell-sub">{fmtTime(r.tao_luc)}</span>
                <span><b>{ACTION_NAME[r.hanh_dong]}</b> · {r.nguoi_bi_tac_dong}</span>
                <span className="lv-cell-sub">{logText(r)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
