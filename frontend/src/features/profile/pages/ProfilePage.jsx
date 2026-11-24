import { useEffect, useState } from "react";

import Icon from "../../../shared/components/Icon.jsx";
import { RANKS, rankOf } from "../../../shared/utils/rank.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { savePlacementGoal } from "../../placement/api/placementApi.js";
import { getPersonalDashboard } from "../../practice/api/practiceApi.js";
import MyReports from "../../reports/components/MyReports.jsx";
import { changePassword, getProfile, saveName, saveReminder } from "../api/profileApi.js";
import LevelUpDialog from "../components/LevelUpDialog.jsx";
import RankBadge from "../components/RankBadge.jsx";
import "../styles/profile.css";

// Cá nhân: quản lý tài khoản, mục tiêu học tập cá nhân hóa (cấp HSK mục tiêu & phút/ngày), nhắc học và danh hiệu KN.
const day = (v) => (v ? new Date(v).toLocaleDateString("vi-VN") : "");
const MINUTE_OPTIONS = [10, 15, 30, 60];

function Note({ msg }) {
  if (!msg) return null;
  return <p className={`pf-note ${msg.ok ? "is-ok" : "is-err"}`} role={msg.ok ? "status" : "alert"}>{msg.ok ? "✓ " : ""}{msg.text}</p>;
}

function NameRow({ token, user, login, value, onSaved }) {
  const [name, setName] = useState(value);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const changed = name.trim() && name.trim() !== value;
  async function submit(e) {
    e.preventDefault();
    setBusy(true); setMsg(null);
    try {
      const res = await saveName(token, name);
      onSaved(res.ho_ten);
      setName(res.ho_ten);
      login({ access_token: token, user: { ...user, ho_ten: res.ho_ten } });
      setMsg({ ok: true, text: "Đã lưu họ tên" });
    } catch (err) { setMsg({ ok: false, text: err.message }); } finally { setBusy(false); }
  }
  return (
    <form className="pf-field" onSubmit={submit}>
      <label htmlFor="pf-name">Họ tên</label>
      <div className="pf-inline">
        <input id="pf-name" value={name} maxLength={100} onChange={(e) => setName(e.target.value)} autoComplete="name" />
        <button type="submit" className="pf-btn" disabled={!changed || busy}>{busy ? "Đang lưu..." : "Lưu"}</button>
      </div>
      <Note msg={msg} />
    </form>
  );
}

function PasswordForm({ token }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ cu: "", moi: "", lai: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  async function submit(e) {
    e.preventDefault();
    if (f.moi !== f.lai) { setMsg({ ok: false, text: "Nhập lại mật khẩu mới chưa khớp" }); return; }
    setBusy(true); setMsg(null);
    try {
      await changePassword(token, f.cu, f.moi);
      setF({ cu: "", moi: "", lai: "" });
      setOpen(false);
      setMsg({ ok: true, text: "Đã đổi mật khẩu" });
    } catch (err) { setMsg({ ok: false, text: err.message }); } finally { setBusy(false); }
  }
  if (!open) {
    return (
      <div className="pf-field">
        <span className="pf-label">Mật khẩu</span>
        <div className="pf-inline"><span className="pf-value">••••••••</span>
          <button type="button" className="pf-btn pf-btn--plain" onClick={() => { setOpen(true); setMsg(null); }}>Đổi mật khẩu</button></div>
        <Note msg={msg} />
      </div>
    );
  }
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <form className="pf-field pf-pass" onSubmit={submit}>
      <span className="pf-label">Đổi mật khẩu</span>
      <input type="password" placeholder="Mật khẩu hiện tại" value={f.cu} onChange={set("cu")} autoComplete="current-password" required aria-label="Mật khẩu hiện tại" />
      <input type="password" placeholder="Mật khẩu mới (từ 8 ký tự, có chữ và số)" value={f.moi} onChange={set("moi")} autoComplete="new-password" required aria-label="Mật khẩu mới" />
      <input type="password" placeholder="Nhập lại mật khẩu mới" value={f.lai} onChange={set("lai")} autoComplete="new-password" required aria-label="Nhập lại mật khẩu mới" />
      <div className="pf-inline">
        <button type="submit" className="pf-btn" disabled={busy}>{busy ? "Đang đổi..." : "Đổi mật khẩu"}</button>
        <button type="button" className="pf-btn pf-btn--plain" onClick={() => { setOpen(false); setMsg(null); }}>Hủy</button>
      </div>
      <Note msg={msg} />
    </form>
  );
}

function PersonalGoalCard({ token }) {
  const [levels, setLevels] = useState([]);
  const [capId, setCapId] = useState("");
  const [minutes, setMinutes] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    const c = new AbortController();
    getPersonalDashboard(token, c.signal)
      .then((d) => {
        setLevels(d.muc_tieu?.danh_sach_cap ?? []);
        setCapId(d.muc_tieu?.cap_muc_tieu_id ? String(d.muc_tieu.cap_muc_tieu_id) : "");
        setMinutes(d.muc_tieu?.phut_moi_ngay ? String(d.muc_tieu.phut_moi_ngay) : "");
      })
      .catch(() => {});
    return () => c.abort();
  }, [token]);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setMsg(null);
    try {
      await savePlacementGoal(token, {
        cap_do_id: capId ? Number(capId) : null,
        phut_moi_ngay: minutes ? Number(minutes) : null,
      });
      setMsg({ ok: true, text: "Đã cập nhật mục tiêu cá nhân hóa. Đề xuất bài học hôm nay sẽ bám sát mục tiêu mới!" });
    } catch (err) {
      setMsg({ ok: false, text: err.message || "Chưa lưu được mục tiêu" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="pf-card" onSubmit={submit}>
      <h2>Mục tiêu cá nhân hóa</h2>
      <p className="pf-muted" style={{ marginBottom: 14 }}>
        Hệ thống dùng mục tiêu này để ưu tiên chọn “Bài phù hợp với bạn hôm nay” và định hướng cấp thi thử.
      </p>
      <div className="pf-field">
        <label htmlFor="pf-goal-cap">Cấp HSK mục tiêu muốn chinh phục</label>
        <select id="pf-goal-cap" value={capId} onChange={(e) => setCapId(e.target.value)} style={{ padding: "9px 12px", borderRadius: 10, border: "1px solid var(--line, #d0d8e4)", background: "var(--paper, #fff)", color: "inherit" }}>
          <option value="">— Chưa chọn mục tiêu cố định —</option>
          {levels.map((lv) => (
            <option key={lv.id} value={lv.id}>{lv.ten}</option>
          ))}
        </select>
      </div>
      <div className="pf-field">
        <label htmlFor="pf-goal-min">Thời lượng luyện tập mỗi ngày</label>
        <select id="pf-goal-min" value={minutes} onChange={(e) => setMinutes(e.target.value)} style={{ padding: "9px 12px", borderRadius: 10, border: "1px solid var(--line, #d0d8e4)", background: "var(--paper, #fff)", color: "inherit" }}>
          <option value="">— Linh hoạt —</option>
          {MINUTE_OPTIONS.map((m) => (
            <option key={m} value={m}>{m} phút / ngày</option>
          ))}
        </select>
      </div>
      <button type="submit" className="pf-btn" disabled={busy}>
        {busy ? "Đang lưu..." : "Lưu mục tiêu học tập"}
      </button>
      <Note msg={msg} />
    </form>
  );
}

function Reminder({ token, value, verified }) {
  const [on, setOn] = useState(value);
  const [msg, setMsg] = useState(null);
  async function toggle() {
    const next = !on;
    setOn(next); setMsg(null);
    try { await saveReminder(token, next); setMsg({ ok: true, text: next ? "Đã bật email nhắc" : "Đã tắt email nhắc" }); }
    catch (err) { setOn(!next); setMsg({ ok: false, text: err.message }); }
  }
  return (
    <div className="pf-card">
      <h2>Nhắc học</h2>
      <div className="pf-switch-row">
        <div>
          <strong>Email nhắc khi vắng học</strong>
          <p>Vắng học 3 ngày, Xiang gửi một email nhắc bạn quay lại.</p>
          {!verified && <p className="pf-warn">Cần xác minh email thì mới nhận được thư nhắc.</p>}
        </div>
        <button type="button" role="switch" aria-checked={on} aria-label="Email nhắc khi vắng học" className={`pf-switch${on ? " is-on" : ""}`} onClick={toggle}>
          <span />
        </button>
      </div>
      <Note msg={msg} />
    </div>
  );
}

export default function ProfilePage() {
  const { token, user, login } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [replay, setReplay] = useState(false);
  const [barIn, setBarIn] = useState(false);

  useEffect(() => {
    const c = new AbortController();
    getProfile(token, c.signal).then((d) => { setData(d); setName(d.ho_ten); requestAnimationFrame(() => setBarIn(true)); })
      .catch((e) => e.name !== "AbortError" && setError(e.message));
    return () => c.abort();
  }, [token]);

  if (error) return <section className="pf"><p role="alert">{error}</p></section>;
  if (!data) return <section className="pf"><p className="pf-muted">Đang tải...</p></section>;
  const rank = rankOf(data.kn);

  return (
    <section className="pf">
      <div className="pf-hero">
        <button type="button" className="pf-hero__badge" onClick={() => setReplay(true)} title="Xem lại hiệu ứng danh hiệu">
          <RankBadge bac={rank.bac} size={132} title={rank.ten} />
        </button>
        <div className="pf-hero__main">
          <h1>{name}</h1>
          <p className="pf-hero__rank"><span>Bậc {rank.bac}/{RANKS.length}</span> <em className="hz">{rank.zh}</em> {rank.ten}</p>
          <p className="pf-muted">Tham gia từ {day(data.tham_gia_luc)}</p>
          <div className="pf-progress">
            <div className="pf-progress__bar"><span style={{ width: barIn ? `${Math.round(rank.ti_le * 100)}%` : 0 }} /></div>
            <small>{rank.next ? <>Còn <b>{rank.con_thieu}</b> KN để lên <b>{rank.next.ten}</b></> : "Bạn đã đạt danh hiệu cao nhất"}</small>
          </div>
        </div>
        <div className="pf-hero__stats">
          <div><Icon name="bolt" size={20} /><b>{data.kn}</b><small>điểm KN</small></div>
          <div><Icon name="flame" size={20} /><b>{data.chuoi_ngay}</b><small>ngày liên tiếp</small></div>
        </div>
      </div>

      <div className="pf-card">
        <h2>Lộ trình danh hiệu</h2>
        <ol className="pf-road">
          {RANKS.map((r, i) => {
            const reached = data.kn >= r.min;
            return (
              <li key={r.ten} className={`${reached ? "is-done" : ""}${i + 1 === rank.bac ? " is-current" : ""}`}>
                <RankBadge bac={i + 1} size={64} locked={!reached} still={i + 1 !== rank.bac}
                  title={reached ? r.ten : `${r.ten}: cần ${r.min} KN (còn ${r.min - data.kn})`} />
                <b className="hz">{r.zh}</b>
                <strong>{r.ten}</strong>
                <small>{r.min.toLocaleString("vi-VN")} KN</small>
              </li>
            );
          })}
        </ol>
        <div
          style={{
            marginTop: 14,
            padding: "12px 15px",
            borderRadius: 14,
            background: "var(--surface-2, rgba(0,0,0,0.03))",
            fontSize: 13.8,
            lineHeight: 1.6,
          }}
        >
          <b style={{ display: "block", marginBottom: 4 }}>Bảng cách tính Điểm kinh nghiệm (KN):</b>
          <div>• Hoàn thành 1 bài ôn luyện thường (đúng hết các câu, lần đầu đạt): <b>+10 KN</b></div>
          <div>• Hoàn thành bài Kiểm tra cuối thửa (10/10 câu, lần đầu đạt): <b>+20 KN</b></div>
          <div>• Đạt bài Kiểm tra vượt thửa / Bắt đầu cấp / Vượt chặng (lần đầu mỗi mốc): <b>+20 KN</b></div>
          <div>• Củng cố thành công 1 câu trong Sổ tay câu sai sang trạng thái Đã củng cố: <b>+1 KN</b></div>
          <div className="pf-muted" style={{ marginTop: 4 }}>
            Mỗi bài/mốc chỉ thưởng KN ở lần đạt đầu tiên; ôn lại bài đã hoàn thành hoàn toàn miễn phí năng lượng và không cộng trùng KN.
          </div>
        </div>
      </div>

      <div className="pf-grid">
        <div className="pf-card">
          <h2>Tài khoản</h2>
          <NameRow token={token} user={user} login={login} value={name} onSaved={setName} />
          <div className="pf-field">
            <span className="pf-label">Email</span>
            <div className="pf-inline"><span className="pf-value">{data.email}</span>
              <span className={`pf-tag${data.email_da_xac_minh ? " is-ok" : ""}`}>{data.email_da_xac_minh ? "Đã xác minh" : "Chưa xác minh"}</span></div>
          </div>
          <div className="pf-field">
            <span className="pf-label">Đăng nhập Google</span>
            <span className="pf-value">{data.lien_ket_google ? "Đã liên kết" : "Chưa liên kết"}</span>
          </div>
          {data.co_mat_khau
            ? <PasswordForm token={token} />
            : <div className="pf-field"><span className="pf-label">Mật khẩu</span><span className="pf-value pf-muted">Tài khoản đăng nhập bằng Google, không dùng mật khẩu</span></div>}
        </div>
        <div style={{ display: "grid", gap: 18, alignContent: "start" }}>
          <PersonalGoalCard token={token} />
          <Reminder token={token} value={data.nhan_email_nhac} verified={data.email_da_xac_minh} />
        </div>
      </div>
      <MyReports />
      {replay && <LevelUpDialog rank={rank} onClose={() => setReplay(false)} />}
    </section>
  );
}
