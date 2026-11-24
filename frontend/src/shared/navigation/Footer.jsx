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
            <p style={{ marginTop: "14px", opacity: 0.8, maxWidth: "30ch" }}>Luyện thi HSK cho người Việt.</p>
          </div>
          <div>
            <h4>Phạm vi đào tạo</h4>
            <ul>
              <li><span>Chứng chỉ HSK 1 – HSK 4</span></li>
              <li><span>Từ vựng · Nghe · Đọc · Viết</span></li>
              <li><span>Trợ giảng AI Xiang cá nhân hóa</span></li>
            </ul>
          </div>
          <div>
            <h4>Tài khoản</h4>
            <ul>
              <li><Link to="/dang-nhap">Đăng nhập</Link></li>
              <li><Link to="/dang-ky">Đăng ký học viên</Link></li>
            </ul>
          </div>
        </div>
        <div className="foot-note"><span>Cấu trúc đề theo chuẩn HSK 2.0.</span></div>
      </div>
    </footer>
  );
}
