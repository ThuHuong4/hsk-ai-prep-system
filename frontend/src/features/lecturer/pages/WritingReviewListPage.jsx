import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { listWriting } from "../api/lecturerApi.js";
import { formatDateTime } from "../utils/labels.js";
import "../styles/lecturer.css";

const TABS = [
  { key: "cho", label: "Phản ánh / chờ kiểm tra" },
  { key: "loi", label: "AI chấm lỗi" },
  { key: "da", label: "Đã kiểm tra" },
  { key: "tat_ca", label: "Tất cả" },
];
const PAGE_SIZE = 20;

export default function WritingReviewListPage() {
  const { token } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = TABS.some((t) => t.key === params.get("tab")) ? params.get("tab") : "cho";
  const [page, setPage] = useState(1);
  const { data, error, loading } = useRequest((signal) => listWriting(token, { tab, trang: page, so_dong: PAGE_SIZE }, signal), [token, tab, page]);
  const pages = Math.max(1, Math.ceil((data?.tong ?? 0) / PAGE_SIZE));

  return (
    <section className="lv-page">
      <div className="lv-page__intro">
        <h1>Chấm bài Viết</h1>
        <p>AI chấm ngay khi học viên làm bài. Giảng viên kiểm tra khi có phản ánh chấm sai: Giữ nguyên hoặc Sửa điểm; mọi lần chấm đều được lưu.</p>
      </div>

      <div className="lv-seg" role="tablist" aria-label="Lọc bài Viết">
        {TABS.map((t) => (
          <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} className={tab === t.key ? "is-active" : undefined}
            onClick={() => { setParams({ tab: t.key }); setPage(1); }}>{t.label}</button>
        ))}
      </div>

      {error && <p role="alert" className="lv-alert">{error}</p>}
      <div className="lv-table">
        <div className="lv-tr lv-tr--head lv-r-grid" aria-hidden="true">
          <span>Bài làm</span><span>Học viên</span><span>Nguồn</span><span>Điểm hiện tại</span><span>Trạng thái</span><span />
        </div>
        {loading && <p className="lv-empty">Đang tải…</p>}
        {!loading && data?.muc.length === 0 && <p className="lv-empty">Không có bài nào trong mục này.</p>}
        {!loading && data?.muc.map((row) => (
          <div className="lv-tr lv-r-grid" key={row.id}>
            <div className="lv-cell-main">
              <span className="lv-cell-icon"><Icon name="pen" /></span>
              <span className="lv-cell-text">
                <Link className="lv-cell-title zh" to={`/giang-vien/cham-viet/${row.id}`}>{row.bai_lam || "(bài trống)"}</Link>
                <span className="lv-cell-sub zh">Đề #{row.ma_cau}: {row.de_bai}</span>
              </span>
            </div>
            <span><span className="lv-cell-label">Học viên</span>{row.hoc_vien}</span>
            <span><span className="lv-cell-label">Nguồn</span>{row.nguon_luot} · {row.ten_cap_do}</span>
            <span>
              <span className="lv-cell-label">Điểm</span>
              {row.diem != null ? <>{row.diem}/{row.diem_toi_da} <span className="lv-cell-sub">({row.nguon_cham === "giang_vien" ? "GV" : "AI"}, {formatDateTime(row.cham_luc)})</span></> : "—"}
            </span>
            <span>
              {row.co_phan_anh_mo && <span className="lv-status lv-status--moi">Có phản ánh</span>}
              {!row.co_phan_anh_mo && row.trang_thai_cham_cuoi === "loi" && <span className="lv-status lv-status--da_an">AI lỗi</span>}
              {!row.co_phan_anh_mo && row.trang_thai_cham_cuoi !== "loi" && (
                <span className={`lv-status lv-status--${row.dat ? "da_dang" : "nhap"}`}>{row.dat ? "Đạt" : "Chưa đạt"}</span>
              )}
            </span>
            <div className="lv-row-actions"><Link className="xbtn xbtn--ghost xbtn--sm" to={`/giang-vien/cham-viet/${row.id}`}>Kiểm tra</Link></div>
          </div>
        ))}
      </div>
      {pages > 1 && (
        <nav className="lv-pager" aria-label="Phân trang">
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Trước</button>
          <span>Trang {page}/{pages}</span>
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Sau</button>
        </nav>
      )}
    </section>
  );
}
