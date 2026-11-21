import { useState } from "react";
import { Link } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { claimMission, getMissions } from "../api/notebookApi.js";
import "../styles/notebook.css";

const ICON = { nv_so_tay: "book", nv_on_luyen: "route", nv_thi_thu: "timer" };

// Nhiệm vụ ngày (mục 4.5): làm xong → "Nhận +1 năng lượng"; đầy 5/5 thì tạm khóa, giữ quyền đến hết ngày
export default function DailyMissions({ compact = false, reloadKey = 0, onClaimed }) {
  const { token } = useAuth();
  const [key, setKey] = useState(0);
  const [busy, setBusy] = useState(null);
  const [note, setNote] = useState("");
  const { data, error } = useRequest((signal) => getMissions(token, signal), [token, key, reloadKey]);

  async function claim(ma) {
    setBusy(ma); setNote("");
    try {
      const res = await claimMission(token, ma);
      setNote(`${res.message} · năng lượng ${res.nang_luong}/5`);
      setKey((k) => k + 1);
      onClaimed?.(res);
      window.dispatchEvent(new Event("xianglingo:stats"));
    } catch (err) {
      setNote(err?.message || "Chưa nhận được");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={`nb-missions${compact ? " is-compact" : ""}`}>
      <div className="nb-missions__head">
        <h2><Icon name="flame" /> Nhiệm vụ hôm nay</h2>
        {data?.nhiem_vu && <span className="nb-energy"><Icon name="sprout" size={16} />{data.nang_luong}/{data.nang_luong_toi_da}</span>}
      </div>
      {error && <p className="xc-muted">Không tải được nhiệm vụ.</p>}
      <ul>
        {data?.nhiem_vu?.map((m) => {
          const full = data.nang_luong >= data.nang_luong_toi_da;
          return (
            <li key={m.ma} className={m.da_nhan ? "is-claimed" : m.xong ? "is-ready" : ""}>
              <span className="nb-mi" aria-hidden="true"><Icon name={ICON[m.ma]} size={18} /></span>
              <span className="nb-mt">
                <b>{m.ten}</b>
                <span className="nb-bar" role="progressbar" aria-valuemin={0} aria-valuemax={m.can} aria-valuenow={m.da_lam}
                  aria-label={m.ten}><i style={{ width: `${(100 * m.da_lam) / m.can}%` }} /></span>
                <small>{m.da_lam}/{m.can}{m.ghi_chu ? ` · ${m.ghi_chu}` : ""}</small>
              </span>
              {m.da_nhan ? <span className="nb-done"><Icon name="check" size={16} />Đã nhận</span>
                : m.xong ? (
                  <button type="button" className="xc-btn xc-btn--sm" disabled={busy === m.ma || full}
                    title={full ? "Năng lượng đang đầy, quyền nhận giữ đến hết hôm nay" : undefined} onClick={() => claim(m.ma)}>
                    {full ? "Đầy 5/5" : "Nhận +1"}
                  </button>
                ) : <Link className="xc-btn xc-btn--plain xc-btn--sm" to={m.duong_dan}>{m.nut}</Link>}
            </li>
          );
        })}
      </ul>
      {note && <p className="nb-note" role="status">{note}</p>}
    </div>
  );
}
