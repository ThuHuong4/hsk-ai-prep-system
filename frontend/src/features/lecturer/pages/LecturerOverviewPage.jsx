import { Link } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { getOverview } from "../api/lecturerApi.js";
import "../styles/lecturer.css";

const TODO = [
  { key: "bao_loi_moi", label: "Báo lỗi nội dung mới", to: "/giang-vien/bao-loi", icon: "alert", urgent: true },
  { key: "cham_sai_cho", label: "Báo chấm sai chờ kiểm tra", to: "/giang-vien/cham-viet", icon: "check", urgent: true },
  { key: "viet_cham_loi", label: "Bài Viết AI chấm lỗi", to: "/giang-vien/cham-viet?tab=loi", icon: "pen", urgent: true },
  { key: "bao_loi_cua_toi", label: "Báo lỗi bạn đang xử lý", to: "/giang-vien/bao-loi?tab=dang", icon: "alert" },
  { key: "de_thieu_du_lieu", label: "Đề nháp thiếu thời lượng hoặc câu", to: "/giang-vien/bo-de?trang_thai=nhap", icon: "timer" },
  { key: "bai_thieu_cau", label: "Bài ôn nháp chưa đủ câu", to: "/giang-vien/bai-luyen", icon: "route" },
  { key: "cau_hoi_nhap", label: "Câu hỏi nháp", to: "/giang-vien/cau-hoi?trang_thai=nhap", icon: "spark" },
  { key: "de_nhap", label: "Đề thi nháp", to: "/giang-vien/bo-de?trang_thai=nhap", icon: "timer" },
  { key: "bai_nhap", label: "Thửa / bài ôn nháp", to: "/giang-vien/bai-luyen", icon: "route" },
  { key: "tai_lieu_nhap", label: "Tài liệu nháp", to: "/giang-vien/hoc-lieu?trang_thai=nhap", icon: "doc" },
  { key: "tu_vung_nhap", label: "Từ vựng nháp", to: "/giang-vien/tu-vung?trang_thai=nhap", icon: "layers" },
];

const TOTALS = [
  { key: "cau_hoi_dang", label: "Câu hỏi đang đăng" },
  { key: "de_dang", label: "Đề thi thử đang đăng" },
  { key: "bai_dang", label: "Bài ôn đang đăng" },
  { key: "tu_vung_xuat_ban", label: "Từ vựng đã xuất bản" },
  { key: "tai_lieu_dang", label: "Tài liệu đang đăng" },
  { key: "cap_do_dang", label: "Cấp độ đang mở" },
];

export default function LecturerOverviewPage() {
  const { token, user } = useAuth();
  const { data, error, loading } = useRequest((signal) => getOverview(token, signal), [token]);
  const todo = data?.viec_can_lam || {};
  const pending = TODO.filter((t) => todo[t.key] > 0);

  return (
    <section className="lv-page">
      <div className="lv-page__intro">
        <h1>Chào {user?.ho_ten}</h1>
        <p>Việc cần làm và số liệu nội dung, cập nhật mỗi lần mở trang.</p>
      </div>
      {error && <p role="alert" className="lv-alert">{error}</p>}
      {loading && <p className="lv-muted">Đang tải…</p>}

      {data && (
        <>
          <h2>Việc cần làm</h2>
          {pending.length === 0 ? (
            <p className="lv-card lv-muted">Không còn việc nào đang chờ.</p>
          ) : (
            <ul className="lv-stat-grid">
              {pending.map((t) => (
                <li key={t.key}>
                  <Link to={t.to} className={`lv-stat${t.urgent ? " is-urgent" : ""}`}>
                    <span className="lv-cell-icon"><Icon name={t.icon} /></span>
                    <span className="lv-stat__num">{todo[t.key]}</span>
                    <span className="lv-stat__label">{t.label}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}

          <h2>Nội dung đang dùng</h2>
          <ul className="lv-stat-grid">
            {TOTALS.map((t) => (
              <li key={t.key}>
                <div className="lv-stat">
                  <span className="lv-stat__num">{data.tong_so[t.key]}</span>
                  <span className="lv-stat__label">{t.label}</span>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
