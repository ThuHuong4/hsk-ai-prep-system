import { useRef } from "react";
import { Link } from "react-router-dom";
import xiangFull from "../../../assets/images/xiang/home/xiang_full.webp";
import xiangHead from "../../../assets/images/xiang/home/xiang_head.webp";
import useHomeEffects from "../hooks/useHomeEffects.js";
import "../styles/publicHome.css";

// Cấu trúc đề HSK 1–4 (thông tin định dạng kỳ thi, không phải số liệu người dùng)
const LEVELS = [
  { n: 1, q: 40, mins: 40, parts: ["Nghe", "Đọc"], c: "#16B2AA", hz: "一" },
  { n: 2, q: 60, mins: 55, parts: ["Nghe", "Đọc"], c: "#EF6F57", hz: "二" },
  { n: 3, q: 80, mins: 90, parts: ["Nghe", "Đọc", "Viết"], c: "#2F4F9A", hz: "三" },
  { n: 4, q: 100, mins: 105, parts: ["Nghe", "Đọc", "Viết"], c: "#E0A030", hz: "四" },
];

function HomeSprite() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true" focusable="false">
      <symbol id="i-flame" viewBox="0 0 24 24"><path d="M12 22a7 7 0 0 0 7-7c0-3-1.6-5.4-4-7.5.2 2-1 3.5-2.4 3.5C11 11 11 8 12.5 2 8 4.5 5 9 5 15a7 7 0 0 0 7 7z"/></symbol>
      <symbol id="i-check" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></symbol>
      <symbol id="i-bolt" viewBox="0 0 24 24"><path d="M13 2 4 13.5h7L10 22l9-11.5h-7z"/></symbol>
      <symbol id="i-arrow" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></symbol>
      <symbol id="grass-art" viewBox="0 0 64 64"><path d="M32 60C29 42 21 28 8 20c11 2 19 10 23 22 1-15-1-27-8-38 11 9 14 23 12 36 4-11 12-19 23-21-11 8-17 19-19 41z" fill="#4FBF7A"/><path d="M32 60c-1-10-1-20 2-30 1 10 1 20 0 30z" fill="#3FA968"/><rect x="21" y="44" width="22" height="7" rx="3.5" fill="#C08E5C"/></symbol>
      <symbol id="tea-art" viewBox="0 0 80 70"><path d="M28 18c-4-5 4-8 0-14M40 18c-4-5 4-8 0-14M52 18c-4-5 4-8 0-14" fill="none" stroke="#8BE6C9" strokeWidth="3" strokeLinecap="round"/><ellipse cx="40" cy="62" rx="34" ry="7" fill="#2CD3C9"/><path d="M14 26h52v8a26 26 0 0 1-52 0z" fill="#FFF7EA" stroke="#E3C79A" strokeWidth="3"/><ellipse cx="40" cy="26" rx="26" ry="5" fill="#9ADB8F"/><path d="M30 40h20" stroke="#EF6F57" strokeWidth="3" strokeLinecap="round"/></symbol>
      <symbol id="book-art" viewBox="0 0 90 70"><path d="M45 12C35 4 18 4 6 8v54c12-4 29-4 39 4 10-8 27-8 39-4V8C72 4 55 4 45 12z" fill="#8DA5FF"/><path d="M45 12v54" stroke="#3E57B4" strokeWidth="2.5"/><path d="M45 14C36 8 22 8 11 11v47c11-3 25-3 34 3 9-6 23-6 34-3V11C68 8 54 8 45 14z" fill="#F4F7FF"/><path d="M17 22h20M17 30h22M17 38h16M53 22h20M53 30h16" stroke="#B8C5F2" strokeWidth="3" strokeLinecap="round"/></symbol>
      <symbol id="brush-art" viewBox="0 0 120 40"><rect x="30" y="14" width="86" height="12" rx="6" fill="#A86B34"/><rect x="30" y="14" width="10" height="12" fill="#2CD3C9"/><path d="M30 12C14 12 4 18 0 20c4 2 14 8 30 8z" fill="#14243D"/><circle cx="110" cy="20" r="3" fill="#FFD99B"/></symbol>
      <symbol id="bamboo-art" viewBox="0 0 160 420"><g fill="var(--bam)"><rect x="40" y="10" width="15" height="410" rx="7"/><rect x="86" y="60" width="12" height="360" rx="6"/><rect x="122" y="120" width="10" height="300" rx="5"/></g><g fill="var(--bam-node)"><rect x="38" y="90" width="19" height="5" rx="2.5"/><rect x="38" y="190" width="19" height="5" rx="2.5"/><rect x="38" y="300" width="19" height="5" rx="2.5"/><rect x="84" y="150" width="16" height="4" rx="2"/><rect x="84" y="260" width="16" height="4" rx="2"/><rect x="120" y="210" width="14" height="4" rx="2"/><rect x="120" y="320" width="14" height="4" rx="2"/></g><g fill="var(--bam-leaf)"><path d="M55 88c22-12 52-14 74-4-24 10-50 12-74 4z"/><path d="M40 60C24 46 4 42-10 46c14 12 34 18 50 14z"/><path d="M98 148c18-14 42-20 62-14-18 14-40 18-62 14z"/><path d="M55 188c16-16 40-24 60-20-16 16-38 22-60 20z"/><path d="M86 120C70 104 50 98 32 100c14 14 34 22 54 20z"/><path d="M132 208c10-14 24-22 36-22-8 14-22 22-36 22z"/><path d="M40 290C26 276 8 270-8 272c12 12 30 20 48 18z"/></g></symbol>
    </svg>
  );
}

export default function PublicHomePage() {
  const rootRef = useRef(null);
  useHomeEffects(rootRef);

  return (
    <div className="xl xl-home" ref={rootRef}>
      <HomeSprite />
      {/* HERO */}
      <section className="h-hero" aria-labelledby="hero-title">
        <div className="wrap h-hero-grid">
          <div className="h-art" id="stage" aria-hidden="true">
            <div className="h-blob"></div>
            <span className="moo" hidden></span>
            <img className="xiang-main" data-depth="-8" src={xiangFull} alt="" />
            <div className="fl f1" data-depth="18"><span className="in"><span className="bubble-w"><span className="hz">你好！</span></span></span></div>
            <div className="fl f2" data-depth="26"><span className="in"><svg width="80" height="70"><use href="#tea-art"/></svg></span></div>
            <div className="fl f3" data-depth="22"><span className="in"><span className="tile-hz t-teal">汉</span></span></div>
            <div className="fl f4" data-depth="30"><span className="in"><span className="tile-hz t-cream">字</span></span></div>
            <div className="fl f5" data-depth="24"><span className="in"><span className="stamp">好</span></span></div>
            <div className="fl f6" data-depth="14"><span className="in"><svg width="78" height="60"><use href="#book-art"/></svg></span></div>
            <div className="fl f7" data-depth="20"><span className="in"><span className="flame-chip"><svg className="ico"><use href="#i-flame"/></svg></span></span></div>
            <span className="dot" style={{ left: "12%", top: "20%", background: "#FFD99B" }}></span><span className="dot" style={{ right: "14%", top: "58%", background: "#8BE6C9" }}></span><span className="dot" style={{ left: "22%", bottom: "12%", background: "#FF8A72" }}></span>
          </div>
          <div className="h-copy">
            <h1 id="hero-title" className="enter" tabIndex="-1">Học HSK theo cách vui nhất, cùng chú trâu Xiang!</h1>
            <div className="h-btns enter d2">
              <Link className="btn btn-xl" to="/dang-ky">Bắt đầu ôn luyện</Link>
              <Link className="btn btn-xl plain" to="/thi-thu">Xem đề thi thử HSK</Link>
              <p className="h-note">Xem đề không cần tài khoản · <Link to="/dang-nhap">Đã có tài khoản? Đăng nhập</Link></p>
            </div>
          </div>
        </div>
        <nav className="h-levels" aria-label="Các cấp HSK">
          <div className="wrap">
            <Link to="/thi-thu/hsk/1" className="lv-link"><span className="lv-ic" style={{ '--c': "#16B2AA" }}>一</span>HSK 1</Link>
            <Link to="/thi-thu/hsk/2" className="lv-link"><span className="lv-ic" style={{ '--c': "#EF6F57" }}>二</span>HSK 2</Link>
            <Link to="/thi-thu/hsk/3" className="lv-link"><span className="lv-ic" style={{ '--c': "#2F4F9A" }}>三</span>HSK 3</Link>
            <Link to="/thi-thu/hsk/4" className="lv-link"><span className="lv-ic" style={{ '--c': "#E0A030" }}>四</span>HSK 4</Link>
            <span className="lv-note">Từ vựng · Nghe · Đọc · Viết</span>
          </div>
        </nav>
      </section>
    
      {/* Đề thi thử trên trang chủ */}
      <section className="h-exams" aria-labelledby="hx-title">
        <div className="wrap">
          <div className="hx-head"><div><span className="eyebrow">Thi thử HSK</span><h2 id="hx-title">Đề thi thử HSK 1–4</h2></div><Link className="gline" to="/thi-thu">Xem tất cả đề</Link></div>
          <div className="pk-grid" id="home-cats">
            {LEVELS.map((d) => (
              <Link key={d.n} className="pk-card cat" to={`/thi-thu/hsk/${d.n}`} style={{ "--c": d.c }} aria-label={`Đề thi thử HSK ${d.n}`}>
                <div className="pk-top"><span className="lv-ic" style={{ "--c": d.c }}>{d.hz}</span><span className="cat-go"><svg className="ico"><use href="#i-arrow" /></svg></span></div>
                <b className="cat-lv">HSK {d.n}</b>
                <span className="cat-main">{d.q} câu · {d.mins} phút</span>
                <span className="cat-sk">{d.parts.join(" · ")}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>
    
      {/* FEATURE 1 */}
      <section className="feat" aria-labelledby="f1-title" id="cach-hoc">
        <div className="wrap feat-grid">
          <div className="feat-copy reveal">
            <h2 id="f1-title">Mỗi ngày một chút</h2>
            <p>Bài học ngắn, vừa sức, xong trong vài phút.</p>
          </div>
          <div className="feat-art reveal" aria-hidden="true">
            <div className="phone">
              <div className="ph-bar"><span className="ph-x">✕</span><span className="ph-prog"><i style={{ width: "58%" }}></i></span><span className="ph-lamp"><svg width="20" height="20"><use href="#grass-art"/></svg>4</span></div>
              <div className="ph-q">Chọn nghĩa đúng</div>
              <div className="ph-word"><span className="hz">谢谢</span><small>xièxie</small></div>
              <div className="ph-opts"><span>Xin chào</span><span className="on">Cảm ơn</span><span>Tạm biệt</span><span>Xin lỗi</span></div>
              <div className="ph-btn">KIỂM TRA</div>
            </div>
            <img className="peek-l" src={xiangHead} alt="" />
            <span className="stamp s-abs">好</span>
          </div>
        </div>
      </section>
    
      {/* FEATURE 2: Xiang cày ruộng chữ (cuộn để cày) */}
      <section className="pl-sec" id="pl-sec" aria-label="Xiang cày ruộng chữ: mỗi luống mọc một cấp HSK từ 1 đến 4">
        <div className="pl-sticky">
          <div className="pl-wrap">
            <div className="pl-scene" id="pl-scene" role="img" aria-label="Xiang kéo cày qua ruộng, phía sau mọc lên các mầm chữ 一 二 三 四">
              <div className="pl-sky"><span className="pl-stars"></span><span className="pl-sun"></span>
                <span className="pl-cloud k1"></span><span className="pl-cloud k2"></span><span className="pl-cloud k3"></span>
                <span className="bird"></span><span className="bird b2"></span></div>
              <svg className="pl-layer mt-far" data-par="18" viewBox="0 0 1320 300" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
                <defs><linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--mist)" stopOpacity="0"/><stop offset="1" stopColor="var(--mist)" stopOpacity=".9"/></linearGradient></defs>
                <path fill="var(--mt1)" d="M0 300 L0 210 C40 200 50 120 90 110 C120 104 130 170 160 180 C190 150 200 70 240 60 C280 52 290 150 320 170 C350 140 370 100 400 96 C440 92 450 170 480 180 C520 130 540 40 590 36 C640 32 650 150 690 172 C720 140 740 110 780 108 C820 106 830 170 860 182 C900 120 920 64 960 58 C1000 54 1010 160 1050 176 C1080 150 1100 120 1140 118 C1180 116 1190 170 1220 186 C1260 150 1280 120 1320 116 L1320 300 Z"/>
                <rect x="0" y="150" width="1320" height="150" fill="url(#mist)"/>
              </svg>
              <svg className="pl-layer mt-mid" data-par="40" viewBox="0 0 1320 300" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
                <path fill="var(--mt2)" d="M0 300 L0 196 C110 150 210 112 330 140 C440 166 520 196 640 168 C760 140 850 104 980 132 C1100 160 1200 184 1320 150 L1320 300 Z"/>
              </svg>
              <div className="pl-paddy"><span className="pl-water"><i></i><i></i><i></i></span></div>
              <div className="pl-ground"></div><div className="pl-row"><span className="pl-done" id="pl-done"></span></div>
              <div className="pl-sprouts">
                <span className="sprout" style={{ '--x': "6%" }}><b className="hz">一</b><small>HSK 1</small></span>
                <span className="sprout" style={{ '--x': "24%" }}><b className="hz">二</b><small>HSK 2</small></span>
                <span className="sprout" style={{ '--x': "42%" }}><b className="hz">三</b><small>HSK 3</small></span>
                <span className="sprout" style={{ '--x': "60%" }}><b className="hz">四</b><small>HSK 4</small></span>
              </div>
              <div className="ox pl-ox" id="pl-ox">
                <svg className="plow" viewBox="0 0 120 70" aria-hidden="true"><path d="M118 18 60 34" stroke="#8B5A2B" strokeWidth="6" strokeLinecap="round"/><path d="M62 30 34 54l-20 6 10-14 30-20z" fill="#A86B34"/><path d="M14 60 2 66l14-2z" fill="#6B7A8C"/><path d="M44 36 40 8" stroke="#8B5A2B" strokeWidth="5" strokeLinecap="round"/><circle cx="40" cy="8" r="5" fill="#A86B34"/></svg>
                <img src={xiangFull} alt="" />
                <span className="dust d1"></span><span className="dust d2"></span>
              </div>
              <svg className="pl-layer pl-bamboo bl" data-par="-30" viewBox="0 0 160 420" aria-hidden="true"><use href="#bamboo-art"/></svg>
              <svg className="pl-layer pl-bamboo br" data-par="-60" viewBox="0 0 160 420" aria-hidden="true"><use href="#bamboo-art"/></svg>
              <svg className="pl-layer pl-front" data-par="-90" viewBox="0 0 1320 80" preserveAspectRatio="none" aria-hidden="true"><path fill="var(--g3)" d="M0 80V40c40-6 60-30 80-10 20-26 40-4 60 0 30-24 50-10 70 4 20-22 50-18 70-2 30-20 50-6 80 4 20-26 50-20 70-2 20-18 50-14 70 2 30-24 60-12 80 2 20-24 50-16 70 0 30-20 50-10 80 4 20-22 40-16 60-2 30-24 60-12 80 0 20-20 50-14 70 2 30-22 50-10 80 2 20-20 40-14 70 0V80z"/></svg>
            </div>
          </div>
        </div>
      </section>
    
      {/* FEATURE: Thi thử */}
      <section className="feat alt" aria-labelledby="fx-title">
        <div className="wrap feat-grid rev">
          <div className="feat-copy reveal">
            <h2 id="fx-title">Thi thử trước ngày thi</h2>
            <p>Làm quen với cấu trúc đề HSK 1–4.</p>
            <Link className="btn exam fx-btn" to="/thi-thu">Xem đề thi thử</Link>
          </div>
          <div className="feat-art reveal" aria-hidden="true">
            <div className="exam-art">
              <svg className="ex-clock" viewBox="0 0 80 80"><circle cx="40" cy="40" r="34" fill="var(--paper)" stroke="#2F4F9A" strokeWidth="6"/><g stroke="#C3D0E8" strokeWidth="3" strokeLinecap="round"><path d="M40 12v6M40 62v6M12 40h6M62 40h6"/></g><path className="hand-m" d="M40 40V20" stroke="#14243D" strokeWidth="4" strokeLinecap="round"/><path d="M40 40l12 8" stroke="#EF6F57" strokeWidth="4" strokeLinecap="round"/><circle cx="40" cy="40" r="4" fill="#14243D"/></svg>
              <div className="ex-head">
                <img src={xiangHead} alt="" />
                <svg className="ex-phones" viewBox="0 0 520 348"><path d="M118 196C112 70 408 70 402 196" fill="none" stroke="#2F4F9A" strokeWidth="18" strokeLinecap="round"/><rect x="92" y="168" width="46" height="84" rx="20" fill="#8DA5FF" stroke="#2F4F9A" strokeWidth="6"/><rect x="382" y="168" width="46" height="84" rx="20" fill="#8DA5FF" stroke="#2F4F9A" strokeWidth="6"/></svg>
              </div>
              <div className="ex-desk">
                <div className="ex-paper"><span className="hz">听力</span><i></i><i></i><i className="s"></i><div className="bub"><b></b><b className="f"></b><b></b><b className="f"></b><b></b><b></b><b className="f"></b><b></b></div></div>
                <svg className="ex-pencil" viewBox="0 0 140 40"><rect x="18" y="10" width="96" height="20" rx="4" fill="#FFD99B"/><rect x="18" y="10" width="96" height="7" rx="3" fill="#F4B24C"/><rect x="104" y="10" width="20" height="20" rx="3" fill="#EF6F57"/><path d="M18 10 2 20l16 10z" fill="#F5D7B5"/><path d="M8 16 2 20l6 4z" fill="#14243D"/></svg>
              </div>
              <span className="stamp ex-seal">考</span>
            </div>
          </div>
        </div>
      </section>
    
      {/* FEATURE 3: Đèn lồng soi chữ */}
      <section className="feat" aria-labelledby="f3-title" id="loi-sai">
        <div className="wrap feat-grid">
          <div className="feat-copy reveal">
            <h2 id="f3-title">Sai đâu, hiểu đó</h2>
            <p>Mỗi lỗi sai đều có lời giải thích dễ hiểu.</p>
          </div>
          <div className="feat-art reveal">
            <div className="night" id="night" style={{ '--x': "30%", '--y': "38%" }}>
              <span className="glowspot" aria-hidden="true"></span>
              <div className="words" role="list">
                <button type="button" role="listitem" className="wd lit" data-i="0"><b className="hz">再见</b><small>zàijiàn · tạm biệt</small></button>
                <button type="button" role="listitem" className="wd" data-i="1"><b className="hz">谢谢</b><small>xièxie · cảm ơn</small></button>
                <button type="button" role="listitem" className="wd" data-i="2"><b className="hz">米饭</b><small>mǐfàn · cơm</small></button>
                <button type="button" role="listitem" className="wd" data-i="3"><b className="hz">老师</b><small>lǎoshī · giáo viên</small></button>
                <button type="button" role="listitem" className="wd" data-i="4"><b className="hz">喝茶</b><small>hē chá · uống trà</small></button>
                <button type="button" role="listitem" className="wd" data-i="5"><b className="hz">朋友</b><small>péngyou · bạn bè</small></button>
              </div>
              <span className="carry" aria-hidden="true"><svg width="96" height="96" viewBox="0 0 96 96"><circle cx="40" cy="40" r="30" fill="rgba(255,255,255,.18)" stroke="#2F4F9A" strokeWidth="7"/><path d="M62 62l24 24" stroke="#EF6F57" strokeWidth="11" strokeLinecap="round"/><path d="M24 30a18 18 0 0 1 12-10" stroke="#fff" strokeWidth="4" strokeLinecap="round" fill="none" opacity=".8"/></svg></span>
              <div className="night-x" aria-hidden="true"><span className="nb" id="night-say">再 là “lại”, 见 là “gặp”: hẹn gặp lại!</span><img src={xiangHead} alt="" /></div>
            </div>
          </div>
        </div>
      </section>
    
      {/* FEATURE 4 */}
      <section className="feat alt" aria-labelledby="f4-title">
        <div className="wrap feat-grid rev">
          <div className="feat-copy reveal">
            <h2 id="f4-title">Học đều, nhớ lâu</h2>
            <p>Xiang nhắc bạn quay lại mỗi ngày và ôn đúng những câu còn quên.</p>
          </div>
          <div className="feat-art reveal" aria-hidden="true">
            <div className="streak">
              <div className="st-top"><span className="st-flame"><svg className="ico"><use href="#i-flame"/></svg></span><div><b>3 ngày liên tiếp</b><small>ví dụ</small></div></div>
              <div className="st-week"><i className="on">T2</i><i className="on">T3</i><i className="on">T4</i><i className="today">T5</i><i>T6</i><i>T7</i><i>CN</i></div>
              <div className="st-lamps"><svg><use href="#grass-art"/></svg><svg><use href="#grass-art"/></svg><svg><use href="#grass-art"/></svg><svg><use href="#grass-art"/></svg><svg className="off"><use href="#grass-art"/></svg></div>
            </div>
            <div className="path-mini"><span className="mm done"><svg className="ico"><use href="#i-check"/></svg></span><span className="ln"></span><span className="mm done"><svg className="ico"><use href="#i-check"/></svg></span><span className="ln"></span><span className="mm now"><svg className="ico"><use href="#i-bolt"/></svg></span></div>
          </div>
        </div>
      </section>
    
      {/* CTA */}
      <section className="h-cta" aria-labelledby="cta-title">
        <div className="wrap" style={{ textAlign: "center" }}>
          <h2 id="cta-title" className="reveal">Sẵn sàng chinh phục HSK cùng Xiang?</h2>
          <div className="reveal" style={{ display: "flex", flexWrap: "wrap", gap: "12px", justifyContent: "center", marginTop: "26px" }}><Link className="btn btn-xl" to="/dang-ky" style={{ width: "auto", padding: "0 32px" }}>Bắt đầu</Link><Link className="btn btn-xl plain" to="/dang-ky" style={{ width: "auto", padding: "0 32px" }}>Đăng ký</Link></div>
        </div>
        <div className="cta-stage" aria-hidden="true">
          <svg className="ground" viewBox="0 0 1440 260" preserveAspectRatio="none"><path d="M0 120 C 220 120 300 120 420 150 C 560 186 600 260 720 260 C 840 260 880 186 1020 150 C 1140 120 1220 120 1440 120 L1440 260 L0 260 Z" fill="var(--ground)"/></svg>
          <img className="cta-x" src={xiangFull} alt="" />
          <div className="fl c1"><span className="in"><svg width="64" height="64"><use href="#grass-art"/></svg></span></div>
          <div className="fl c2"><span className="in"><span className="tile-hz t-teal">学</span></span></div>
          <div className="fl c3"><span className="in"><span className="stamp">好</span></span></div>
          <div className="fl c4"><span className="in"><span className="tile-hz t-cream">习</span></span></div>
          <div className="fl c5"><span className="in"><span className="flame-chip"><svg className="ico"><use href="#i-flame"/></svg></span></span></div>
          <div className="fl c6"><span className="in"><svg width="72" height="56"><use href="#book-art"/></svg></span></div>
          <div className="fl c7"><span className="in"><svg width="110" height="37"><use href="#brush-art"/></svg></span></div>
        </div>
      </section>
    </div>
  );
}
