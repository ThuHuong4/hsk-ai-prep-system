import { useState } from "react";
import { Link } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../lecturer/styles/lecturer.css";
import { listRoles, renameRole } from "../api/adminApi.js";
import "../styles/admin.css";

// Vai trò: bảng riêng để mở rộng. Quyền gắn với mã vai trò trong code nên chỉ cho đổi tên hiển thị.
export default function RolesPage() {
  const { token } = useAuth();
  const [reloadKey, setReloadKey] = useState(0);
  const [editing, setEditing] = useState(null); // { id, ten }
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const { data, error, loading } = useRequest((signal) => listRoles(token, signal), [token, reloadKey]);

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await renameRole(token, editing.id, editing.ten.trim());
      setMessage({ type: "ok", text: res.message });
      setEditing(null);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setMessage({ type: "bad", text: err?.message || "Không lưu được" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="lv-page">
      <div className="lv-page__intro">
        <h1>Vai trò</h1>
        <p>Vai trò được tách thành bảng riêng để mở rộng. Quyền của mỗi vai trò cố định theo nghiệp vụ; Quản trị viên đổi được tên hiển thị.</p>
      </div>
      {message.text && <p role={message.type === "ok" ? "status" : "alert"} className={message.type === "ok" ? "lv-notice" : "lv-alert"}>{message.text}</p>}
      {error && <p role="alert" className="lv-alert">{error}</p>}
      {loading && <p className="lv-muted">Đang tải…</p>}
      <ul className="ad-roles">
        {data?.map((r) => (
          <li key={r.id} className="ad-role-card">
            <div className="ad-role-card__head">
              {editing?.id === r.id ? (
                <form className="ad-role-edit" onSubmit={save}>
                  <input aria-label="Tên vai trò" value={editing.ten} maxLength={50} autoFocus
                    onChange={(e) => setEditing({ ...editing, ten: e.target.value })} />
                  <button type="submit" className="xbtn xbtn--sm" disabled={busy || editing.ten.trim().length < 2}>Lưu</button>
                  <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => setEditing(null)}>Hủy</button>
                </form>
              ) : (
                <>
                  <span className={`ad-role ad-role--${r.id}`}>{r.ten}</span>
                  <code className="ad-code">{r.ma}</code>
                  <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => setEditing({ id: r.id, ten: r.ten })}>Đổi tên</button>
                </>
              )}
            </div>
            <p>{r.mo_ta}</p>
            <Link className="ad-role-card__count" to={`/quan-tri/tai-khoan?vai_tro=${r.id}`}>{r.so_tai_khoan} tài khoản</Link>
          </li>
        ))}
      </ul>
      <p className="lv-muted ad-foot">Thêm vai trò mới (ví dụ Trợ giảng) cần bổ sung bảng quyền gắn với vai trò ở giai đoạn sau.</p>
    </section>
  );
}
