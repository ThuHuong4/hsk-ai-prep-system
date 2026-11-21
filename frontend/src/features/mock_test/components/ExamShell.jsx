import { useTheme } from "../../../shared/theme.js";
import { Link } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import Icon from "../../../shared/components/Icon.jsx";
import "../../../layouts/staffShell.css";
import "../../lecturer/styles/lecturer.css";
import "../styles/mockTest.css";

export { readTheme } from "../../../shared/theme.js";

// Khung trang làm bài/xem kết quả: toàn màn hình, không thanh bên để tập trung
export default function ExamShell({ title, right, children }) {
  const [theme, toggle] = useTheme();
  return (
    <div className="xg xt" data-theme={theme}>
      <header className="xt-top">
        <Link to="/hoc-vien" className="xt-brand" aria-label="Xianglingo – về trang Học viên">
          <span className="xg-brand__face"><img src={xiangFace} alt="" /></span>
        </Link>
        <span className="xt-top__title">{title}</span>
        <span className="xt-top__right">
          {right}
          <button type="button" className="xg-icon-btn" onClick={toggle} aria-label={theme === "dark" ? "Giao diện sáng" : "Giao diện tối"}>
            <Icon name={theme === "dark" ? "sun" : "moon"} />
          </button>
        </span>
      </header>
      <div className="xt-body">{children}</div>
    </div>
  );
}
