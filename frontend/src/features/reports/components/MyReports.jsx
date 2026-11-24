import { useEffect, useState } from "react";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { listMyReports } from "../api/reportsApi.js";
import "../styles/reports.css";

const RESULT = { da_sua: "Đã sửa câu hỏi", khong_phai_loi: "Không phải lỗi" };

function status(r) {
  if (r.xu_ly_luc) return RESULT[r.ket_luan] || "Đã xử lý";
  return r.nhan_luc ? "Giảng viên đang xử lý" : "Chờ tiếp nhận";
}

// Danh sách báo lỗi học viên đã gửi kèm kết luận và phản hồi của Giảng viên (trang Cá nhân)
export default function MyReports() {
  const { token } = useAuth();
  const [items, setItems] = useState(null);
  useEffect(() => {
    const c = new AbortController();
    listMyReports(token, c.signal).then((d) => setItems(d.muc || [])).catch(() => setItems([]));
    return () => c.abort();
  }, [token]);

  if (!items || items.length === 0) return null;
  return (
    <div className="pf-card rq-mine">
      <h2>Báo lỗi đã gửi</h2>
      <ul>
        {items.map((r) => (
          <li key={r.id}>
            <div className="rq-mine__top">
              <span className="hz">{r.noi_dung_cau || "Câu hỏi"}</span>
              <span className={`rq-tag${r.xu_ly_luc ? " is-done" : ""}`}>{status(r)}</span>
            </div>
            <small>{r.ly_do}</small>
            {r.phan_hoi && <p className="rq-reply"><b>Giảng viên phản hồi:</b> {r.phan_hoi}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}
