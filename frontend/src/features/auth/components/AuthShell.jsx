import { Link } from "react-router-dom";

import xiangFull from "../../../assets/images/xiang/home/xiang_full.webp";
import "../styles/auth.css";

function AuthSprite() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true" focusable="false">
      <symbol id="i-arrow" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></symbol>
      <symbol id="i-mail" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m4 7 8 6 8-6"/></symbol>
      <symbol id="i-key" viewBox="0 0 24 24"><rect x="4" y="10.5" width="16" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/><circle cx="12" cy="15.5" r="1.2"/></symbol>
      <symbol id="i-eye" viewBox="0 0 24 24"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></symbol>
      <symbol id="i-eyeoff" viewBox="0 0 24 24"><path d="M3 3l18 18"/><path d="M10.6 5.1A10.8 10.8 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.2 4.1M6.6 6.6C3.8 8.4 2 12 2 12s3.6 7 10 7a9.6 9.6 0 0 0 5.4-1.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/></symbol>
      <symbol id="i-id" viewBox="0 0 24 24"><circle cx="12" cy="9" r="3.5"/><path d="M5.5 20a6.5 6.5 0 0 1 13 0"/></symbol>
      <symbol id="i-check" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></symbol>
      <symbol id="i-alert" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9.5"/><path d="M12 7.5v5.5M12 16.5h.01"/></symbol>
      <symbol id="bamboo-art" viewBox="0 0 160 420"><g fill="var(--bam)"><rect x="40" y="10" width="15" height="410" rx="7"/><rect x="86" y="60" width="12" height="360" rx="6"/><rect x="122" y="120" width="10" height="300" rx="5"/></g><g fill="var(--bam-node)"><rect x="38" y="90" width="19" height="5" rx="2.5"/><rect x="38" y="190" width="19" height="5" rx="2.5"/><rect x="38" y="300" width="19" height="5" rx="2.5"/><rect x="84" y="150" width="16" height="4" rx="2"/><rect x="84" y="260" width="16" height="4" rx="2"/><rect x="120" y="210" width="14" height="4" rx="2"/><rect x="120" y="320" width="14" height="4" rx="2"/></g><g fill="var(--bam-leaf)"><path d="M55 88c22-12 52-14 74-4-24 10-50 12-74 4z"/><path d="M40 60C24 46 4 42-10 46c14 12 34 18 50 14z"/><path d="M98 148c18-14 42-20 62-14-18 14-40 18-62 14z"/><path d="M55 188c16-16 40-24 60-20-16 16-38 22-60 20z"/><path d="M86 120C70 104 50 98 32 100c14 14 34 22 54 20z"/><path d="M132 208c10-14 24-22 36-22-8 14-22 22-36 22z"/><path d="M40 290C26 276 8 270-8 272c12 12 30 20 48 18z"/></g></symbol>
      <symbol id="tea-art" viewBox="0 0 80 70"><path d="M28 18c-4-5 4-8 0-14M40 18c-4-5 4-8 0-14M52 18c-4-5 4-8 0-14" fill="none" stroke="#8BE6C9" strokeWidth="3" strokeLinecap="round"/><ellipse cx="40" cy="62" rx="34" ry="7" fill="#2CD3C9"/><path d="M14 26h52v8a26 26 0 0 1-52 0z" fill="#FFF7EA" stroke="#E3C79A" strokeWidth="3"/><ellipse cx="40" cy="26" rx="26" ry="5" fill="#9ADB8F"/><path d="M30 40h20" stroke="#EF6F57" strokeWidth="3" strokeLinecap="round"/></symbol>

    </svg>
  );
}

// Khung chung Đăng nhập / Đăng ký theo bản mô phỏng: cảnh ruộng có Xiang bên trái, thẻ form bên phải
export default function AuthShell({ mode, mood = "", tilt = 0, children }) {
  return (
    <div className="xa">
      <AuthSprite />
      <div className="au">
        <div className={`au-art${mood ? " " + mood : ""}`} style={{ "--tilt": `${tilt}deg` }} aria-hidden="true">
        <span className="pl-stars"></span><span className="pl-sun"></span>
        <span className="pl-cloud k1"></span><span className="pl-cloud k2"></span>
        <svg className="pl-layer mt-far" viewBox="0 0 1320 300" preserveAspectRatio="xMidYMax slice"><defs><linearGradient id="mist2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--mist)" stopOpacity="0"/><stop offset="1" stopColor="var(--mist)" stopOpacity=".9"/></linearGradient></defs><path fill="var(--mt1)" d="M0 300 L0 210 C40 200 50 120 90 110 C120 104 130 170 160 180 C190 150 200 70 240 60 C280 52 290 150 320 170 C350 140 370 100 400 96 C440 92 450 170 480 180 C520 130 540 40 590 36 C640 32 650 150 690 172 C720 140 740 110 780 108 C820 106 830 170 860 182 C900 120 920 64 960 58 C1000 54 1010 160 1050 176 C1080 150 1100 120 1140 118 C1180 116 1190 170 1220 186 C1260 150 1280 120 1320 116 L1320 300 Z"/><rect x="0" y="150" width="1320" height="150" fill="url(#mist2)"/></svg>
        <svg className="pl-layer mt-mid" viewBox="0 0 1320 300" preserveAspectRatio="xMidYMax slice"><path fill="var(--mt2)" d="M0 300 L0 196 C110 150 210 112 330 140 C440 166 520 196 640 168 C760 140 850 104 980 132 C1100 160 1200 184 1320 150 L1320 300 Z"/></svg>
        <div className="pl-paddy au-paddy"><span className="pl-water"><i></i><i></i><i></i></span></div>
        <div className="au-ground"></div>
        <svg className="pl-layer pl-bamboo bl" viewBox="0 0 160 420"><use href="#bamboo-art"/></svg>
        <svg className="pl-layer pl-bamboo br" viewBox="0 0 160 420"><use href="#bamboo-art"/></svg>
        <div className="fl au-f1"><span className="in"><span className="tile-hz t-teal">学</span></span></div>
        <div className="fl au-f2"><span className="in"><span className="stamp">好</span></span></div>
        <div className="fl au-f3"><span className="in"><svg width="76" height="66"><use href="#tea-art"/></svg></span></div>
        <img className="au-x" src={xiangFull} alt="" />
        <svg className="pl-layer pl-front" viewBox="0 0 1320 80" preserveAspectRatio="none"><path fill="var(--g3)" d="M0 80V40c40-6 60-30 80-10 20-26 40-4 60 0 30-24 50-10 70 4 20-22 50-18 70-2 30-20 50-6 80 4 20-26 50-20 70-2 20-18 50-14 70 2 30-24 60-12 80 2 20-24 50-16 70 0 30-20 50-10 80 4 20-22 40-16 60-2 30-24 60-12 80 0 20-20 50-14 70 2 30-22 50-10 80 2 20-20 40-14 70 0V80z"/></svg>
        </div>
        <div className="au-main">
          <div className="au-card">
            <div className="au-top">
              <Link className="back" to="/"><svg className="ico"><use href="#i-arrow" /></svg>Trang chủ</Link>
            </div>
            <nav className="seg au-seg" data-mode={mode} aria-label="Chọn đăng nhập hoặc đăng ký">
              <span className="knob" aria-hidden="true"></span>
              <Link to="/dang-nhap" aria-current={mode === "login" ? "page" : undefined}>Đăng nhập</Link>
              <Link to="/dang-ky" aria-current={mode === "reg" ? "page" : undefined}>Đăng ký</Link>
            </nav>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
