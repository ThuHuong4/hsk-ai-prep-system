import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { deleteQuestion, listQuestions, questionAction } from "../api/lecturerApi.js";
import StatusBadge from "../components/StatusBadge.jsx";
import { DANG_LABELS, SKILL_LABELS, STATUS_LABELS } from "../utils/labels.js";
import { useLevels } from "../hooks/useLevels.js";
import "../styles/lecturer.css";
import CreatorTag from "../components/CreatorTag.jsx";

const PAGE_SIZE = 20;
const ROW_ICON = { ngu_lieu: "layers", viet_mo: "pen" };

function rowIcon(item) {
  if (ROW_ICON[item.dang]) return ROW_ICON[item.dang];
  if (item.co_audio) return "audio";
  if (item.co_hinh) return "image";
  return "info";
}

function usedFor(item) {
  const tags = [];
  if (item.dung_thi_thu) tags.push("Thi thử");
  if (item.dung_on_luyen) tags.push("Ôn luyện");
  if (item.dung_dau_vao) tags.push("Đầu vào");
  return tags;
}

export default function QuestionListPage() {
  const { token } = useAuth();
  const levels = useLevels();
  const [params] = useSearchParams();
  const [filters, setFilters] = useState({ cap_do_id: "", ky_nang: "", dang: "", trang_thai: params.get("trang_thai") || "", q: "" });
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const [busyId, setBusyId] = useState(null);
  const [message, setMessage] = useState({ type: "", text: "" });

  const { data, error, loading } = useRequest(
    (signal) => listQuestions(token, { ...filters, trang: page, so_dong: PAGE_SIZE }, signal),
    [token, JSON.stringify(filters), page, reloadKey],
  );

  function setFilter(name, value) {
    setFilters((f) => ({ ...f, [name]: value }));
    setPage(1);
  }

  async function act(item, action) {
    if (action === "xoa" && !window.confirm("Xóa bản nháp này? Không hoàn tác được.")) return;
    setBusyId(item.id);
    setMessage({ type: "", text: "" });
    try {
      const res = action === "xoa" ? await deleteQuestion(token, item.id) : await questionAction(token, item.id, action);
      setMessage({ type: "ok", text: res.message });
      setReloadKey((k) => k + 1);
    } catch (err) {
      setMessage({ type: "bad", text: err?.message || "Thao tác thất bại" });
    } finally {
      setBusyId(null);
    }
  }

  const total = data?.tong ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="lv-page">
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Ngân hàng câu hỏi</h1>
          <p>Câu hỏi dùng chung cho Thi thử, Ôn luyện và đánh giá đầu vào. Sửa câu đã đăng sẽ tạo phiên bản nháp mới.</p>
        </div>
        <Link className="xbtn" to="/giang-vien/cau-hoi/moi"><Icon name="plus" /> Thêm câu hỏi</Link>
      </div>

      <div className="lv-filters">
        <form className="lv-searchbox" role="search" onSubmit={(e) => { e.preventDefault(); setFilter("q", search.trim()); }}>
          <Icon name="search" />
          <input type="search" placeholder="Tìm theo nội dung hoặc mã câu" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Tìm câu hỏi" />
        </form>
        <select aria-label="Cấp độ" value={filters.cap_do_id} onChange={(e) => setFilter("cap_do_id", e.target.value)}>
          <option value="">Mọi cấp</option>
          {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
        </select>
        <select aria-label="Kỹ năng" value={filters.ky_nang} onChange={(e) => setFilter("ky_nang", e.target.value)}>
          <option value="">Mọi kỹ năng</option>
          {Object.entries(SKILL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select aria-label="Dạng câu" value={filters.dang} onChange={(e) => setFilter("dang", e.target.value)}>
          <option value="">Mọi dạng</option>
          {Object.entries(DANG_LABELS).filter(([k]) => k !== "chon_bo_chung").map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select aria-label="Trạng thái" value={filters.trang_thai} onChange={(e) => setFilter("trang_thai", e.target.value)}>
          <option value="">Mọi trạng thái</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {message.text && <p role={message.type === "ok" ? "status" : "alert"} className={message.type === "ok" ? "lv-notice" : "lv-alert"}>{message.text}</p>}
      {error && <p role="alert" className="lv-alert">{error}</p>}

      <div className="lv-table">
        <div className="lv-tr lv-tr--head lv-q-grid" aria-hidden="true">
          <span>Câu hỏi</span><span>Cấp</span><span>Kỹ năng</span><span>Dạng</span><span>Dùng trong</span><span>Trạng thái</span><span />
        </div>
        {loading && <p className="lv-empty">Đang tải…</p>}
        {!loading && data?.muc.length === 0 && <p className="lv-empty">Chưa có câu hỏi nào khớp bộ lọc.</p>}
        {!loading && data?.muc.map((item) => (
          <div className="lv-tr lv-q-grid" key={item.id}>
            <div className="lv-cell-main">
              <span className="lv-cell-icon"><Icon name={rowIcon(item)} /></span>
              <span className="lv-cell-text">
                <Link className="lv-cell-title zh" to={`/giang-vien/cau-hoi/${item.id}`}>
                  {item.tom_tat || (item.co_audio ? "(Câu nghe)" : item.co_hinh ? "(Câu hình)" : "(Chưa có nội dung)")}
                </Link>
                <span className="lv-cell-sub">
                  #{item.ma_goc_id}{item.phien_ban > 1 && ` · bản ${item.phien_ban}`}
                  {item.so_cau_con > 0 && ` · ${item.so_cau_con} câu con`}
                  {item.trang_thai === "nhap" && item.co_ban_dang_dung && " · đang có bản đăng"}
                </span>
                <CreatorTag creator={item.nguoi_tao} editor={item.nguoi_sua} />
              </span>
            </div>
            <span><span className="lv-cell-label">Cấp</span>{item.ten_cap_do}</span>
            <span><span className="lv-cell-label">Kỹ năng</span>{SKILL_LABELS[item.ky_nang]}</span>
            <span><span className="lv-cell-label">Dạng</span>{DANG_LABELS[item.dang]}</span>
            <span>
              <span className="lv-cell-label">Dùng trong</span>
              {usedFor(item).length ? usedFor(item).map((t) => <span className="lv-tag" key={t}>{t}</span>) : <span className="lv-muted">Chưa chọn</span>}
            </span>
            <span><StatusBadge status={item.trang_thai} /></span>
            <div className="lv-row-actions">
              <Link className="xbtn xbtn--ghost xbtn--sm" to={`/giang-vien/cau-hoi/${item.id}`}>Sửa</Link>
              {item.trang_thai === "nhap" && (
                <>
                  <button type="button" className="xbtn xbtn--sm" disabled={busyId === item.id} onClick={() => act(item, "dang")}>Đăng</button>
                  <button type="button" className="xbtn xbtn--danger xbtn--sm" disabled={busyId === item.id} onClick={() => act(item, "xoa")}>Xoá</button>
                </>
              )}
              {item.trang_thai === "da_dang" && (
                <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busyId === item.id} onClick={() => act(item, "an")}>Ẩn</button>
              )}
              {item.trang_thai === "da_an" && (
                <button type="button" className="xbtn xbtn--sm" disabled={busyId === item.id} onClick={() => act(item, "hien")}>Hiện lại</button>
              )}
            </div>
          </div>
        ))}
      </div>

      {pages > 1 && (
        <nav className="lv-pager" aria-label="Phân trang">
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Trước</button>
          <span>Trang {page}/{pages} · {total} câu</span>
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Sau</button>
        </nav>
      )}
    </section>
  );
}
