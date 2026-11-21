import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../lecturer/styles/lecturer.css";
import { changeRole, createLecturer, listAccounts, lockAccount, unlockAccount } from "../api/adminApi.js";
import AccountDetail from "./AccountDetail.jsx";
import "../styles/admin.css";
import { ROLE_NAME, fmtTime } from "../utils/labels.js";

// Tài khoản (mục 6.7): tìm/lọc, đổi Học viên ↔ Giảng viên, khóa/mở khóa; không sửa mình và Quản trị viên khác
export default function AccountsPage() {
  const { token, user } = useAuth();
  const [params] = useSearchParams();
  const [filters, setFilters] = useState({ q: "", vai_tro: params.get("vai_tro") || "", trang_thai: params.get("trang_thai") || "", trang: 1 });
  const [search, setSearch] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [dialog, setDialog] = useState(null); // { row, kind: "khoa" | "mo_khoa" | "vai_tro" }
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [detailId, setDetailId] = useState(null);
  const [adding, setAdding] = useState(null); // { ho_ten, email }
  const { data, error, loading } = useRequest((signal) => listAccounts(token, filters, signal), [token, JSON.stringify(filters), reloadKey]);

  const pages = data ? Math.max(1, Math.ceil(data.tong / data.so_moi_trang)) : 1;
  const editable = (row) => row.id !== user?.ma_nguoi_dung && row.vai_tro_id !== 2;

  function open(row, kind) { setDialog({ row, kind }); setReason(""); }

  async function addLecturer(e) {
    e.preventDefault();
    setBusy(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await createLecturer(token, { ho_ten: adding.ho_ten.trim(), email: adding.email.trim() });
      setMessage({ type: res.da_gui_email ? "ok" : "bad", text: `${res.message}: ${adding.email.trim()}` });
      setAdding(null);
      setFilters((f) => ({ ...f, vai_tro: "", trang_thai: "", q: "", trang: 1 }));
      setReloadKey((k) => k + 1);
    } catch (err) {
      setMessage({ type: "bad", text: err?.message || "Không tạo được tài khoản" });
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    const { row, kind } = dialog;
    setBusy(true);
    setMessage({ type: "", text: "" });
    try {
      let res;
      if (kind === "khoa") res = await lockAccount(token, row.id, reason.trim());
      else if (kind === "mo_khoa") res = await unlockAccount(token, row.id, reason.trim());
      else res = await changeRole(token, row.id, row.vai_tro_id === 1 ? 3 : 1, reason.trim());
      setMessage({ type: "ok", text: `${res.message}: ${row.ho_ten}` });
      setDialog(null);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setMessage({ type: "bad", text: err?.message || "Thao tác thất bại" });
      setDialog(null);
    } finally {
      setBusy(false);
    }
  }

  const title = dialog && (dialog.kind === "khoa" ? "Khóa tài khoản?" : dialog.kind === "mo_khoa" ? "Mở khóa tài khoản?"
    : `Đổi thành ${ROLE_NAME[dialog.row.vai_tro_id === 1 ? 3 : 1]}?`);
  const hint = dialog && (dialog.kind === "khoa" ? "Người này bị đăng xuất và không đăng nhập được cho tới khi mở khóa. Dữ liệu học tập được giữ nguyên."
    : dialog.kind === "mo_khoa" ? "Người này đăng nhập lại được bình thường."
    : dialog.row.vai_tro_id === 1 ? "Người này cần đăng nhập lại để vào khu Giảng viên; tiến độ học tập vẫn giữ."
    : "Người này cần đăng nhập lại để vào khu Học viên; nội dung đã soạn vẫn giữ, Giảng viên khác vẫn quản lý được.");

  return (
    <section className="lv-page">
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Tài khoản</h1>
          <p>Bấm vào tên để xem hồ sơ. Không sửa tài khoản của mình và của Quản trị viên khác.</p>
        </div>
        <button type="button" className="xbtn" onClick={() => setAdding({ ho_ten: "", email: "" })}><Icon name="plus" /> Thêm giảng viên</button>
      </div>

      <div className="lv-filters">
        <form className="lv-searchbox" role="search" onSubmit={(e) => { e.preventDefault(); setFilters((f) => ({ ...f, q: search.trim(), trang: 1 })); }}>
          <Icon name="search" />
          <input type="search" placeholder="Tìm theo tên hoặc email" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Tìm tài khoản" />
        </form>
        <select aria-label="Vai trò" value={filters.vai_tro} onChange={(e) => setFilters((f) => ({ ...f, vai_tro: e.target.value, trang: 1 }))}>
          <option value="">Mọi vai trò</option>
          <option value="1">Học viên</option>
          <option value="3">Giảng viên</option>
          <option value="2">Quản trị viên</option>
        </select>
        <select aria-label="Trạng thái" value={filters.trang_thai} onChange={(e) => setFilters((f) => ({ ...f, trang_thai: e.target.value, trang: 1 }))}>
          <option value="">Mọi trạng thái</option>
          <option value="hoat_dong">Hoạt động</option>
          <option value="khoa">Bị khóa</option>
        </select>
      </div>

      {message.text && <p role={message.type === "ok" ? "status" : "alert"} className={message.type === "ok" ? "lv-notice" : "lv-alert"}>{message.text}</p>}
      {error && <p role="alert" className="lv-alert">{error}</p>}

      <div className="lv-table">
        <div className="lv-tr lv-tr--head ad-grid" aria-hidden="true">
          <span>Tài khoản</span><span>Vai trò</span><span>Trạng thái</span><span>Ngày tạo</span><span />
        </div>
        {loading && <p className="lv-empty">Đang tải…</p>}
        {!loading && data?.tai_khoan.length === 0 && <p className="lv-empty">Không có tài khoản phù hợp.</p>}
        {!loading && data?.tai_khoan.map((row) => (
          <div className="lv-tr ad-grid" key={row.id}>
            <button type="button" className="lv-cell-main ad-linkbtn" onClick={() => setDetailId(row.id)}>
              <span className="lv-cell-icon"><Icon name="user" /></span>
              <span className="lv-cell-text">
                <span className="lv-cell-title">{row.ho_ten}{row.id === user?.ma_nguoi_dung && <span className="ad-me"> (bạn)</span>}</span>
                <span className="lv-cell-sub">{row.email}</span>
                <span className="ad-tags">
                  {row.co_google && <span className="ad-tag">Google</span>}
                  {row.co_mat_khau && <span className="ad-tag">Mật khẩu</span>}
                  <span className="ad-tag">{row.da_xac_minh ? "Đã xác minh email" : "Chưa xác minh email"}</span>
                </span>
              </span>
            </button>
            <span><span className="lv-cell-label">Vai trò</span><span className={`ad-role ad-role--${row.vai_tro_id}`}>{row.ten_vai_tro || ROLE_NAME[row.vai_tro_id]}</span></span>
            <span><span className="lv-cell-label">Trạng thái</span><span className={`ad-state ad-state--${row.trang_thai}`}>{row.trang_thai === "khoa" ? "Bị khóa" : "Hoạt động"}</span></span>
            <span><span className="lv-cell-label">Ngày tạo</span>{fmtTime(row.tao_luc)}</span>
            <div className="lv-row-actions">
              {editable(row) ? (
                <>
                  <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => open(row, "vai_tro")}>
                    Đổi thành {ROLE_NAME[row.vai_tro_id === 1 ? 3 : 1]}
                  </button>
                  {row.trang_thai === "khoa"
                    ? <button type="button" className="xbtn xbtn--sm" onClick={() => open(row, "mo_khoa")}>Mở khóa</button>
                    : <button type="button" className="xbtn xbtn--danger xbtn--sm" onClick={() => open(row, "khoa")}>Khóa</button>}
                </>
              ) : <span className="lv-cell-sub">Không sửa được</span>}
            </div>
          </div>
        ))}
      </div>

      {data && pages > 1 && (
        <div className="ad-pager">
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={filters.trang <= 1} onClick={() => setFilters((f) => ({ ...f, trang: f.trang - 1 }))}>Trước</button>
          <span>Trang {filters.trang}/{pages} · {data.tong} tài khoản</span>
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={filters.trang >= pages} onClick={() => setFilters((f) => ({ ...f, trang: f.trang + 1 }))}>Sau</button>
        </div>
      )}

      {detailId && (
        <AccountDetail id={detailId} reloadKey={reloadKey} onClose={() => setDetailId(null)} onAction={open}
          editable={detailId !== user?.ma_nguoi_dung && data?.tai_khoan.find((r) => r.id === detailId)?.vai_tro_id !== 2} />
      )}

      {adding && (
        <div className="ad-modal" role="dialog" aria-modal="true" aria-labelledby="ad-add">
          <form className="ad-modal__box" onSubmit={addLecturer}>
            <h2 id="ad-add">Thêm giảng viên</h2>
            <p>Hệ thống tạo tài khoản Giảng viên và gửi email để giảng viên <b>tự đặt mật khẩu</b>. Quản trị viên không biết mật khẩu.</p>
            <div className="ad-form">
              <label htmlFor="ad-name">Họ tên</label>
              <input id="ad-name" required minLength={2} maxLength={100} value={adding.ho_ten} autoFocus
                onChange={(e) => setAdding({ ...adding, ho_ten: e.target.value })} />
            </div>
            <div className="ad-form">
              <label htmlFor="ad-email">Email</label>
              <input id="ad-email" type="email" required maxLength={255} value={adding.email}
                onChange={(e) => setAdding({ ...adding, email: e.target.value })} />
            </div>
            <div className="ad-modal__acts">
              <button type="button" className="xbtn xbtn--ghost" onClick={() => setAdding(null)} disabled={busy}>Hủy</button>
              <button type="submit" className="xbtn" disabled={busy || adding.ho_ten.trim().length < 2 || !adding.email.trim()}>
                {busy ? "Đang tạo…" : "Tạo và gửi email"}
              </button>
            </div>
          </form>
        </div>
      )}

      {dialog && (
        <div className="ad-modal ad-modal--top" role="dialog" aria-modal="true" aria-labelledby="ad-dlg">
          <div className="ad-modal__box">
            <h2 id="ad-dlg">{title}</h2>
            <p><b>{dialog.row.ho_ten}</b> · {dialog.row.email}</p>
            <p>{hint}</p>
            <label htmlFor="ad-reason">Lý do (ghi vào nhật ký, không bắt buộc)</label>
            <input id="ad-reason" maxLength={255} value={reason} onChange={(e) => setReason(e.target.value)} />
            <div className="ad-modal__acts">
              <button type="button" className="xbtn xbtn--ghost" onClick={() => setDialog(null)} disabled={busy}>Hủy</button>
              <button type="button" className={`xbtn${dialog.kind === "khoa" ? " xbtn--danger" : ""}`} onClick={confirm} disabled={busy}>
                {busy ? "Đang lưu…" : "Xác nhận"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
