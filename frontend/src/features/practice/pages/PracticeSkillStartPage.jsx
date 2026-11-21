import { Link, useParams } from "react-router-dom";

import Icon from "../../../shared/components/Icon.jsx";
import "../../exam_catalog/styles/catalog.css";
import { parseLevelId } from "../../exam_catalog/utils/levels.js";
import { findSkill } from "../skills.js";

export default function PracticeSkillStartPage({ basePath, guest }) {
  const { maCapDo, kyNang } = useParams();
  const level = parseLevelId(maCapDo);
  const skill = findSkill(kyNang);
  const invalid = !level || !skill || (skill.minLevel && level < skill.minLevel);

  return (
    <section className="xc">
      <Link className="xc-back" to={level ? `${basePath}/hsk/${level}` : basePath}>
        <Icon name="arrowLeft" />Chọn kỹ năng khác
      </Link>
      {invalid ? (
        <p role="alert">Nội dung không hợp lệ hoặc chưa áp dụng cho cấp này.</p>
      ) : (
        <>
          <header className="xc-head"><h1>{skill.label} – HSK {level}</h1></header>
          <p role="status" className="xc-muted">
            {guest ? "Bài mẫu ngắn đang phát triển." : "Lộ trình các bậc đang phát triển."}
          </p>
          {guest && (
            <p className="xc-muted">
              Kết quả bài mẫu không được lưu vào tài khoản. Đăng nhập để lưu tiến độ học tập.
            </p>
          )}
        </>
      )}
    </section>
  );
}