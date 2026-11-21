import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import xiangFace from "../assets/images/xiang/home/xiang_face.webp";
import VerifyEmailBanner from "../features/auth/components/VerifyEmailBanner.jsx";
import { useAuth } from "../features/auth/context/AuthContext.jsx";
import Icon from "../shared/components/Icon.jsx";
import BackButton from "../shared/components/BackButton.jsx";
import ScrollNav from "../shared/components/ScrollNav.jsx";
import { useTheme } from "../shared/theme.js";
import "./staffShell.css";

// Khung trang theo bản mô phỏng: thanh bên + thanh trên. tabs = điện thoại dùng thanh tab ở đáy (Học viên)
export default function StaffLayout({ roleLabel, menu, badges = {}, tabs = false, variant = "", topExtra = null }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [theme, toggleTheme] = useTheme();
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => setNavOpen(false), [location.pathname]);

  function handleLogout() {
    logout();
    navigate("/dang-nhap", { replace: true });
  }

  const current = [...menu]
    .sort((a, b) => b.to.length - a.to.length)
    .find((item) => (item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)));
  const initial = (user?.ho_ten || "?").trim().charAt(0).toUpperCase();

  return (
    <div className={`xg${tabs ? " xg--tabs" : ""}${variant ? ` xg--${variant}` : ""}`} data-theme={theme}>
      <aside className={`xg-side${navOpen ? " is-open" : ""}`} aria-label={`Menu ${roleLabel}`}>
        <Link to="/" className="xg-brand" aria-label="Xianglingo – Trang chủ">
          <span className="xg-brand__face"><img src={xiangFace} alt="" /></span>
          <span>Xiang<b>lingo</b></span>
        </Link>
        <span className="xg-role">{roleLabel}</span>
        <nav className="xg-nav">
          {menu.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? "is-active" : undefined)}>
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.badge && badges[item.badge] > 0 && <span className="xg-badge" aria-label={`${badges[item.badge]} việc chờ`}>{badges[item.badge]}</span>}
            </NavLink>
          ))}
        </nav>
        <button type="button" className="xg-logout" onClick={handleLogout}>
          <Icon name="logout" />
          <span>Đăng xuất</span>
        </button>
      </aside>
      {navOpen && <button type="button" className="xg-scrim" aria-label="Đóng menu" onClick={() => setNavOpen(false)} />}

      <div className="xg-main">
        <header className="xg-top">
          <button type="button" className="xg-icon-btn xg-menu-btn" aria-label="Mở menu" aria-expanded={navOpen} onClick={() => setNavOpen(true)}>
            <Icon name="menu" />
          </button>
          {location.pathname !== menu[0]?.to && <BackButton home={menu[0]?.to || "/"} className="xg-icon-btn" />}
          <span className="xg-top__title">{current?.label ?? roleLabel}</span>
          <span className="xg-top__user">{user?.ho_ten}</span>
          {topExtra}
          <button type="button" className="xg-icon-btn" onClick={toggleTheme}
            aria-label={theme === "dark" ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}>
            <Icon name={theme === "dark" ? "sun" : "moon"} />
          </button>
          <span className="xg-avatar" aria-hidden="true">{initial}</span>
        </header>
        <VerifyEmailBanner />
        <main className="xg-content">
          <Outlet />
        </main>
      </div>
      <ScrollNav raised={tabs} />
      {tabs && (
        <nav className="xg-tabs" aria-label={`Menu nhanh ${roleLabel}`}>
          {menu.filter((item) => item.tab).map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? "is-active" : undefined)}>
              <Icon name={item.icon} size={22} />
              <span>{item.label}</span>
            </NavLink>
          ))}
          <button type="button" className={menu.some((item) => !item.tab && location.pathname.startsWith(item.to)) ? "is-active" : undefined}
            aria-expanded={navOpen} onClick={() => setNavOpen(true)}>
            <Icon name="menu" size={22} />
            <span>Thêm</span>
          </button>
        </nav>
      )}
    </div>
  );
}
