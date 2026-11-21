import { useState } from "react";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { getAccount, resendInvite } from "../api/adminApi.js";
import { ACTION_NAME, ROLE_NAME, fmtTime, logText } from "../utils/labels.js";

const SURVEY = { chua_lam: "Chưa làm", bo_qua: "Đã bỏ qua", da_tra_loi: "Đã trả lời" };

// Hồ sơ tài khoản: thông tin quản lý + nhật ký; không mở dữ liệu học tập cá nhân
export default function AccountDetail({ id, editable, reloadKey, onClose, onAction }) {
  const { token } = useAuth();
  const [note, setNote] = useState({ type: "", text: "" });
  const [busy, setBusy] = useState(false);
  const { data, error } = useRequest((signal) => getAccount(token, id, signal), [token, id, reloadKey]);

  async function resend() {
    setBusy(true);
    try {
      const res = await resendInvite(token, id);
      setNote({ type: "ok", text: res.message });
    } catch (err) {
      setNote({ type: "bad", text: err?.message || "Không gửi được" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ad-drawer" role="dialog" aria-modal="true" aria-labelledby="ad-detail" onClick={onClose}>
      <aside className="ad-drawer__panel" onClick={(e) => e.stopPropagation()}>
        <div className="ad-drawer__head">
          <h2 id="ad-detail">Hồ sơ tài khoản</h2>
          <button type="button" className="xbtn xbtn--ghost xbtn--sm" aria-label="Đóng" onClick={onClose}><Icon name="x" /></button>
        </div>
        {error && <p role="alert" className="lv-alert">{error}</p>}
        {!data && !error && <p className="lv-muted">Đang tải…</p>}
        {data && (
          <>
            <div className="ad-profile">
              <span className="ad-avatar" aria-hidden="true">{((data.ho_ten || "?").trim().split(/\s+/).pop() || "?").charAt(0).toUpperCase()}</span>
              <div>
                <b>{data.ho_ten}</b>
                <span>{data.email}</span>
              </div>
            </div>
            <dl className="ad-dl">
              <dt>Vai trò</dt><dd><span className={`ad-role ad-role--${data.vai_tro_id}`}>{data.ten_vai_tro || ROLE_NAME[data.vai_tro_id]}</span></dd>
              <dt>Trạng thái</dt><dd><span className={`ad-state ad-state--${data.trang_thai}`}>{data.trang_thai === "khoa" ? "Bị khóa" : "Hoạt động"}</span></dd>
              <dt>Đăng nhập bằng</dt><dd>{[data.co_mat_khau && "Mật khẩu", data.co_google && "Google"].filter(Boolean).join(", ") || "—"}</dd>
              <dt>Xác minh email</dt><dd>{data.email_xac_minh_luc ? fmtTime(data.email_xac_minh_luc) : "Chưa xác minh"}</dd>
              <dt>Ngày tạo</dt><dd>{fmtTime(data.tao_luc)}</dd>
              {data.vai_tro_id === 1 && <><dt>Khảo sát đầu vào</dt><dd>{SURVEY[data.ks_trang_thai]}</dd></>}
            </dl>
            {editable && (
              <div className="ad-drawer__acts">
                <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => onAction(data, "vai_tro")}>
                  Đổi thành {ROLE_NAME[data.vai_tro_id === 1 ? 3 : 1]}
                </button>
                {data.trang_thai === "khoa"
                  ? <button type="button" className="xbtn xbtn--sm" onClick={() => onAction(data, "mo_khoa")}>Mở khóa</button>
                  : <button type="button" className="xbtn xbtn--danger xbtn--sm" onClick={() => onAction(data, "khoa")}>Khóa</button>}
                {data.vai_tro_id === 3 && data.co_mat_khau && data.trang_thai === "hoat_dong" && (
                  <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={busy} onClick={resend}>Gửi lại email đặt mật khẩu</button>
                )}
              </div>
            )}
            {note.text && <p role={note.type === "ok" ? "status" : "alert"} className={note.type === "ok" ? "lv-notice" : "lv-alert"}>{note.text}</p>}
            <h3>Nhật ký tài khoản</h3>
            {data.nhat_ky.length === 0 ? <p className="lv-muted">Chưa có thao tác quản trị nào.</p> : (
              <ul className="ad-timeline">
                {data.nhat_ky.map((l) => (
                  <li key={l.id}>
                    <b>{ACTION_NAME[l.hanh_dong]}</b> · {logText(l)}
                    <small>{fmtTime(l.tao_luc)} · {l.nguoi_thao_tac}{l.ly_do ? ` · ${l.ly_do}` : ""}</small>
                  </li>
                ))}
              </ul>
            )}
            <p className="lv-muted ad-foot">Quản trị viên không xem bài làm, điểm hay Sổ tay của từng học viên.</p>
          </>
        )}
      </aside>
    </div>
  );
}
