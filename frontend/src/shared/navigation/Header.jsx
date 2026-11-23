import { Link, NavLink } from "react-router-dom";

import xiangFace from "../../assets/images/xiang/home/xiang_face.webp";
import { useAuth } from "../../features/auth/context/AuthContext.jsx";
import DictionaryButton from "../../features/search/components/DictionaryButton.jsx";
import { homePathForRole } from "../../features/auth/utils/roles.js";
import { useTheme } from "../hooks/useTheme.js";
import "./siteShell.css";

export default function Header() {
  const { user } = useAuth();
  const home = user ? homePathForRole(user.vai_tro) : null;
  const [theme, toggleTheme] = useTheme();

  return (
    <header className="xs site-head">
      <div className="wrap">
        <Link className="brand" to="/" aria-label="Xianglingo – Trang chủ">
          <span className="face"><img src={xiangFace} alt="" /></span>
          <span>Xiang<b>lingo</b></span>
        </Link>
        <nav className="mainnav" aria-label="Điều hướng chính">
          <NavLink to="/thi-thu">Thi thử</NavLink>
          <NavLink to="/on-luyen">Ôn luyện</NavLink>
        </nav>
        <div className="head-actions">
          <DictionaryButton />
          <button type="button" className="theme-tg" onClick={toggleTheme}
            aria-label={theme === "dark" ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}
            title={theme === "dark" ? "Giao diện sáng" : "Giao diện tối"}>
            {theme === "dark" ? (
              <svg className="ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5" /><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" /></svg>
            ) : (
              <svg className="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
            )}
          </button>
          {user ? (
            home && <span className="ha-user"><Link className="btn sm" to={home}>Vào trang của tôi</Link></span>
          ) : (
            <span className="ha-user">
              <Link className="gline hide-sm" to="/dang-nhap">Đăng nhập</Link>
              <Link className="btn sm" to="/dang-ky">Đăng ký</Link>
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
