import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { deleteExam, examAction, listExams } from "../api/lecturerApi.js";
import StatusBadge from "../components/StatusBadge.jsx";
import { STATUS_LABELS } from "../utils/labels.js";
import { useLevels } from "../utils/useLevels.js";
import "../styles/lecturer.css";
import CreatorTag from "../components/CreatorTag.jsx";

export default function LecturerExamListPage() {
  const { token } = useAuth();
  const levels = useLevels();
  const [params] = useSearchParams();
  const [filters, setFilters] = useState({ cap_do_id: "", trang_thai: params.get("trang_thai") || "", q: "" });
  const [search, setSearch] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [busyId, setBusyId] = useState(null);
  const [message, setMessage] = useState({ type: "", text: "" });
  const { data, error, loading } = useRequest(
    (signal) => listExams(token, filters, signal),
    [token, JSON.stringify(filters), reloadKey],
  );

  async function act(exam, action) {
    if (action === "xoa" && !window.confirm("Xóa đề nháp này?")) return;
    setBusyId(exam.id);
    setMessage({ type: "", text: "" });
    try {
      const res = action === "xoa" ? await deleteExam(token, exam.id) : await examAction(token, exam.id, action);
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
          <h1>Đề thi thử HSK</h1>
          <p>Ghép câu đã đăng thành đề theo từng cấp. Đề đã đăng muốn sửa thì tạo bản nháp mới, bản cũ vẫn dùng đến khi đăng bản mới.</p>
        </div>
        <Link className="xbtn" to="/giang-vien/bo-de/moi"><Icon name="plus" /> Tạo đề</Link>
      </div>

      <div className="lv-filters">
        <form className="lv-searchbox" role="search" onSubmit={(e) => { e.preventDefault(); setFilters((f) => ({ ...f, q: search.trim() })); }}>
          <Icon name="search" />
          <input type="search" placeholder="Tìm theo tên hoặc mã đề" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Tìm đề" />
        </form>
        <select aria-label="Cấp độ" value={filters.cap_do_id} onChange={(e) => setFilters((f) => ({ ...f, cap_do_id: e.target.value }))}>
          <option value="">Mọi cấp</option>
          {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
        </select>
        <select aria-label="Trạng thái" value={filters.trang_thai} onChange={(e) => setFilters((f) => ({ ...f, trang_thai: e.target.value }))}>
          <option value="">Mọi trạng thái</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {message.text && <p role={message.type === "ok" ? "status" : "alert"} className={message.type === "ok" ? "lv-notice" : "lv-alert"}>{message.text}</p>}
      {error && <p role="alert" className="lv-alert">{error}</p>}

      <div className="lv-table">
        <div className="lv-tr lv-tr--head lv-e-grid" aria-hidden="true">
          <span>Đề thi</span><span>Cấp</span><span>Số câu</span><span>Thời lượng</span><span>Trạng thái</span><span />
        </div>
        {loading && <p className="lv-empty">Đang tải…</p>}
        {!loading && data?.length === 0 && <p className="lv-empty">Chưa có đề nào.</p>}
        {!loading && data?.map((exam) => (
          <div className="lv-tr lv-e-grid" key={exam.id}>
            <div className="lv-cell-main">
              <span className="lv-cell-icon"><Icon name="timer" /></span>
              <span className="lv-cell-text">
                <Link className="lv-cell-title" to={`/giang-vien/bo-de/${exam.id}`}>{exam.ten}</Link>
                <span className="lv-cell-sub">
                  {exam.ma_de}{exam.phien_ban > 1 && ` · bản ${exam.phien_ban}`}
                  {exam.trang_thai === "nhap" && exam.co_ban_dang_dung && " · đang có bản đăng"}
                </span>
                <CreatorTag creator={exam.nguoi_tao} editor={exam.nguoi_sua} />
              </span>
            </div>
            <span><span className="lv-cell-label">Cấp</span>{exam.ten_cap_do}</span>
            <span><span className="lv-cell-label">Số câu</span>{exam.so_cau}</span>
            <span><span className="lv-cell-label">Thời lượng</span>{exam.thoi_luong_phut ? `${exam.thoi_luong_phut} phút` : "—"}</span>
            <span><StatusBadge status={exam.trang_thai} /></span>
            <div className="lv-row-actions">
              <Link className="xbtn xbtn--ghost xbtn--sm" to={`/giang-vien/bo-de/${exam.id}`}>{exam.trang_thai === "nhap" ? "Sửa" : "Xem"}</Link>
              {exam.trang_thai === "nhap" && (
                <button type="button" className="xbtn xbtn--danger xbtn--sm" disabled={busyId === exam.id} onClick={() => act(exam, "xoa")}>Xoá</button>
              )}
              {exam.trang_thai === "da_dang" && (
                <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busyId === exam.id} onClick={() => act(exam, "an")}>Ẩn</button>
              )}
              {exam.trang_thai === "da_an" && (
                <button type="button" className="xbtn xbtn--sm" disabled={busyId === exam.id} onClick={() => act(exam, "hien")}>Hiện lại</button>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
