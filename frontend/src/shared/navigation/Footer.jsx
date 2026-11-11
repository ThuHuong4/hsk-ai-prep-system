import { Link } from "react-router-dom";

import xiangFace from "../../assets/images/xiang/home/xiang_face.webp";
import "./siteShell.css";

export default function Footer() {
  return (
    <footer className="xs foot">
      <div className="wrap">
        <div className="foot-grid">
          <div>
            <Link className="brand" to="/">
              <span className="face"><img src={xiangFace} alt="" /></span>
              <span>Xiang<b>lingo</b></span>
            </Link>
            <p style={{ marginTop: "14px", opacity: 0.8, maxWidth: "30ch" }}>Luyện thi HSK 1–4 cho người Việt.</p>
          </div>
          <div>
            <h4>Học</h4>
            <ul>
              <li><Link to="/on-luyen">Ôn luyện</Link></li>
              <li><a href="/#loi-sai">Ôn câu sai</a></li>
              <li><Link to="/thi-thu">HSK 1–4</Link></li>
            </ul>
          </div>
          <div>
            <h4>Tài khoản</h4>
            <ul>
              <li><Link to="/dang-nhap">Đăng nhập</Link></li>
              <li><Link to="/dang-ky">Tạo tài khoản</Link></li>
            </ul>
          </div>
        </div>
        <div className="foot-note"><span>Cấu trúc đề theo chuẩn HSK 2.0.</span></div>
      </div>
    </footer>
  );
}
