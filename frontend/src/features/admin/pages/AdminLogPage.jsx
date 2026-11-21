import { useState } from "react";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../lecturer/styles/lecturer.css";
import { listAdminLogs } from "../api/adminApi.js";
import "../styles/admin.css";
import { ACTION_NAME, fmtTime, logText } from "../utils/labels.js";

// Nhật ký quản trị: ai làm gì, với tài khoản nào, cũ → mới, khi nào
export default function AdminLogPage() {
  const { token } = useAuth();
  const [filters, setFilters] = useState({ hanh_dong: "", q: "" });
  const [search, setSearch] = useState("");
  const { data, error, loading } = useRequest((signal) => listAdminLogs(token, filters, signal), [token, JSON.stringify(filters)]);

  return (
    <section className="lv-page">
      <div className="lv-page__intro">
        <h1>Nhật ký quản trị</h1>
        <p>Mỗi lần khóa, mở khóa, đổi vai trò đều được ghi lại (100 dòng mới nhất).</p>
      </div>
      <div className="lv-filters">
        <form className="lv-searchbox" role="search" onSubmit={(e) => { e.preventDefault(); setFilters((f) => ({ ...f, q: search.trim() })); }}>
          <Icon name="search" />
          <input type="search" placeholder="Tìm theo tên hoặc email" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Tìm trong nhật ký" />
        </form>
        <select aria-label="Thao tác" value={filters.hanh_dong} onChange={(e) => setFilters((f) => ({ ...f, hanh_dong: e.target.value }))}>
          <option value="">Mọi thao tác</option>
          {Object.entries(ACTION_NAME).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      {error && <p role="alert" className="lv-alert">{error}</p>}
      <div className="lv-table">
        <div className="lv-tr lv-tr--head ad-log-grid" aria-hidden="true">
          <span>Thời điểm</span><span>Thao tác</span><span>Tài khoản bị tác động</span><span>Cũ → mới</span><span>Người thao tác · lý do</span>
        </div>
        {loading && <p className="lv-empty">Đang tải…</p>}
        {!loading && data?.length === 0 && <p className="lv-empty">Chưa có thao tác nào.</p>}
        {!loading && data?.map((r) => (
          <div className="lv-tr ad-log-grid" key={r.id}>
            <span>{fmtTime(r.tao_luc)}</span>
            <span><b>{ACTION_NAME[r.hanh_dong]}</b></span>
            <span className="lv-cell-text"><span className="lv-cell-title">{r.nguoi_bi_tac_dong}</span><span className="lv-cell-sub">{r.email_bi_tac_dong}</span></span>
            <span>{logText(r)}</span>
            <span className="lv-cell-text"><span>{r.nguoi_thao_tac}</span><span className="lv-cell-sub">{r.ly_do || "Không ghi lý do"}</span></span>
          </div>
        ))}
      </div>
    </section>
  );
}
