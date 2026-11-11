import { Link, useParams } from "react-router-dom";

import { parseLevelId } from "../../exam_catalog/utils/levels.js";
import { findSkill } from "../skills.js";

export default function PracticeSkillStartPage({ basePath, guest }) {
  const { maCapDo, kyNang } = useParams();
  const level = parseLevelId(maCapDo);
  const skill = findSkill(kyNang);
  const invalid = !level || !skill || (skill.minLevel && level < skill.minLevel);

  return (
    <section>
      <Link className="back-link" to={level ? `${basePath}/hsk/${level}` : basePath}>
        ← Chọn kỹ năng khác
      </Link>
      {invalid ? (
        <p role="alert">Nội dung không hợp lệ hoặc chưa áp dụng cho cấp này.</p>
      ) : (
        <>
          <h1>{skill.label} – HSK {level}</h1>
          <p role="status" className="muted">
            {guest ? "Bài mẫu ngắn đang phát triển." : "Lộ trình các bậc đang phát triển."}
          </p>
          {guest && (
            <p className="muted">
              Kết quả bài mẫu không được lưu vào tài khoản. Đăng nhập để lưu tiến độ học tập.
            </p>
          )}
        </>
      )}
    </section>
  );
}