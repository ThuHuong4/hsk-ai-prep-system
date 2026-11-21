import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { deleteMaterial, listMaterials, materialAction } from "../api/lecturerApi.js";
import StatusBadge from "../components/StatusBadge.jsx";
import { FILE_TYPE_LABELS, SKILL_LABELS, STATUS_LABELS } from "../utils/labels.js";
import { useLevels } from "../utils/useLevels.js";
import "../styles/lecturer.css";
import CreatorTag from "../components/CreatorTag.jsx";

const TYPE_ICON = { pdf: "doc", png: "image", jpg: "image", mp3: "audio", wav: "audio" };

export default function MaterialListPage() {
  const { token } = useAuth();
  const levels = useLevels();
  const [params] = useSearchParams();
  const [filters, setFilters] = useState({ cap_do_id: "", ky_nang: "", trang_thai: params.get("trang_thai") || "", q: "" });
  const [search, setSearch] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [busyId, setBusyId] = useState(null);
  const [message, setMessage] = useState({ type: "", text: "" });
  const { data, error, loading } = useRequest((signal) => listMaterials(token, filters, signal), [token, JSON.stringify(filters), reloadKey]);

  async function act(row, action) {
    if (action === "xoa" && !window.confirm(`Xóa tài liệu "${row.ten}"?`)) return;
    setBusyId(row.id);
    setMessage({ type: "", text: "" });
    try {
      const res = action === "xoa" ? await deleteMaterial(token, row.id) : await materialAction(token, row.id, action);
      setMessage({ type: "ok", text: res.message });
      setReloadKey((k) => k + 1);
    } catch (err) {
      setMessage({ type: "bad", text: err?.message || "Thao tác thất bại" });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="lv-page">
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Tài liệu ôn tập</h1>
          <p>PDF, ảnh và audio đọc thêm (tối đa 20 MB). Học viên chỉ xem sau khi đăng nhập; mỗi bài ôn gắn tối đa một tài liệu.</p>
        </div>
        <Link className="xbtn" to="/giang-vien/hoc-lieu/moi"><Icon name="plus" /> Thêm tài liệu</Link>
      </div>

      <div className="lv-filters">
        <form className="lv-searchbox" role="search" onSubmit={(e) => { e.preventDefault(); setFilters((f) => ({ ...f, q: search.trim() })); }}>
          <Icon name="search" />
          <input type="search" placeholder="Tìm theo tên, mô tả, nguồn" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Tìm tài liệu" />
        </form>
        <select aria-label="Cấp độ" value={filters.cap_do_id} onChange={(e) => setFilters((f) => ({ ...f, cap_do_id: e.target.value }))}>
          <option value="">Mọi cấp</option>
          {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
        </select>
        <select aria-label="Kỹ năng" value={filters.ky_nang} onChange={(e) => setFilters((f) => ({ ...f, ky_nang: e.target.value }))}>
          <option value="">Mọi kỹ năng</option>
          {Object.entries(SKILL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select aria-label="Trạng thái" value={filters.trang_thai} onChange={(e) => setFilters((f) => ({ ...f, trang_thai: e.target.value }))}>
          <option value="">Mọi trạng thái</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {message.text && <p role={message.type === "ok" ? "status" : "alert"} className={message.type === "ok" ? "lv-notice" : "lv-alert"}>{message.text}</p>}
      {error && <p role="alert" className="lv-alert">{error}</p>}

      <div className="lv-table">
        <div className="lv-tr lv-tr--head lv-m-grid" aria-hidden="true">
          <span>Tài liệu</span><span>Cấp</span><span>Kỹ năng</span><span>Loại</span><span>Dùng trong</span><span>Trạng thái</span><span />
        </div>
        {loading && <p className="lv-empty">Đang tải…</p>}
        {!loading && data?.length === 0 && <p className="lv-empty">Chưa có tài liệu nào.</p>}
        {!loading && data?.map((row) => (
          <div className="lv-tr lv-m-grid" key={row.id}>
            <div className="lv-cell-main">
              <span className="lv-cell-icon"><Icon name={TYPE_ICON[row.loai_tep]} /></span>
              <span className="lv-cell-text">
                <Link className="lv-cell-title" to={`/giang-vien/hoc-lieu/${row.id}`}>{row.ten}</Link>
                <span className="lv-cell-sub">{row.mo_ta || "Chưa có mô tả"}{row.phien_ban > 1 && ` · bản ${row.phien_ban}`}</span>
                <CreatorTag creator={row.nguoi_tao} editor={row.nguoi_sua} />
              </span>
            </div>
            <span><span className="lv-cell-label">Cấp</span>{row.ten_cap_do || "—"}</span>
            <span><span className="lv-cell-label">Kỹ năng</span>{SKILL_LABELS[row.ky_nang] || "—"}</span>
            <span><span className="lv-cell-label">Loại</span>{FILE_TYPE_LABELS[row.loai_tep]}</span>
            <span><span className="lv-cell-label">Dùng trong</span>{row.so_bai ? `${row.so_bai} bài` : "Chưa dùng"}</span>
            <span><StatusBadge status={row.trang_thai} /></span>
            <div className="lv-row-actions">
              <Link className="xbtn xbtn--ghost xbtn--sm" to={`/giang-vien/hoc-lieu/${row.id}`}>Xem / Sửa</Link>
              {row.trang_thai === "nhap" && <button type="button" className="xbtn xbtn--sm" disabled={busyId === row.id} onClick={() => act(row, "dang")}>Đăng</button>}
              {row.trang_thai === "da_dang" && <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busyId === row.id} onClick={() => act(row, "an")}>Ẩn khỏi học viên</button>}
              {row.trang_thai === "da_an" && <button type="button" className="xbtn xbtn--sm" disabled={busyId === row.id} onClick={() => act(row, "hien")}>Hiện lại</button>}
              {row.trang_thai === "nhap" && !row.so_bai && <button type="button" className="xbtn xbtn--danger xbtn--sm" disabled={busyId === row.id} onClick={() => act(row, "xoa")}>Xoá</button>}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
