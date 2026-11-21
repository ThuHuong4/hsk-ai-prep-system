import { Link } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import "../styles/auth.css";
import { AuthSprite } from "./AuthShell.jsx";

// Thẻ nhỏ canh giữa cho Quên mật khẩu / Đặt lại mật khẩu / Xác minh email (cùng kiểu khung Đăng nhập)
export default function AuthCard({ title, lead, children }) {
  return (
    <div className="xa">
      <AuthSprite />
      <div className="ac">
        <span className="ac-face" aria-hidden="true"><img src={xiangFace} alt="" /></span>
        <div className="ac-card">
          <Link className="back" to="/dang-nhap"><svg className="ico"><use href="#i-arrow" /></svg>Đăng nhập</Link>
          <h1>{title}</h1>
          {lead && <p className="lead">{lead}</p>}
          {children}
        </div>
      </div>
    </div>
  );
}

export function Notice({ kind, children }) {
  return (
    <div className={`alert ${kind}`} role={kind === "bad" ? "alert" : "status"}>
      <svg className="ico" aria-hidden="true"><use href={kind === "ok" ? "#i-check" : "#i-alert"} /></svg>
      <div>{children}</div>
    </div>
  );
}
