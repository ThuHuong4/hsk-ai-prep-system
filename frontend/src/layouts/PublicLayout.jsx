import { Outlet, useLocation } from "react-router-dom";
import Footer from "../shared/navigation/Footer.jsx";
import Header from "../shared/navigation/Header.jsx";
import BackButton from "../shared/components/BackButton.jsx";
import ScrollNav from "../shared/components/ScrollNav.jsx";
import "./publicLayout.css";

export default function PublicLayout() {
  const { pathname } = useLocation();
  // Trang chủ và các trang tài khoản hiển thị tràn màn hình; các trang công khai khác giữ khung nội dung
  const FULL = ["/", "/dang-nhap", "/dang-ky", "/quen-mat-khau", "/dat-lai-mat-khau", "/xac-minh-email"];
  const mainClass = FULL.includes(pathname) ? "public-layout__main public-layout__main--full" : "public-layout__main";

  return (
    <div className="public-layout">
      <Header />
      <main className={mainClass}>
        {!FULL.includes(pathname) && <BackButton className="pub-back" />}
        <Outlet />
      </main>
      <Footer />
      <ScrollNav />
    </div>
  );
}