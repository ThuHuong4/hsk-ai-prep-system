import { Link, useParams } from "react-router-dom";

import { parseLevelId } from "../../exam_catalog/utils/levels.js";
import { PRACTICE_SKILLS } from "../skills.js";

export default function PracticeSkillPickerPage({ basePath }) {
  const { maCapDo } = useParams();
  const level = parseLevelId(maCapDo);

  if (!level) {
    return (
      <section>
        <Link className="back-link" to={basePath}>← Chọn cấp</Link>
        <p role="alert">Cấp độ không hợp lệ.</p>
      </section>
    );
  }

  return (
    <section>
      <Link className="back-link" to={basePath}>← Chọn cấp khác</Link>
      <h1>Ôn luyện HSK {level}</h1>
      <p className="muted">Chọn kỹ năng muốn luyện.</p>
      <ul className="card-grid">
        {PRACTICE_SKILLS.map((skill) => {
          const locked = skill.minLevel && level < skill.minLevel;
          return (
            <li key={skill.slug}>
              {locked ? (
                <div className="card" aria-disabled="true">
                  <span className="card__title">{skill.label}</span>
                  <span>Nội dung Viết áp dụng từ HSK {skill.minLevel}</span>
                </div>
              ) : (
                <Link className="card" to={`${basePath}/hsk/${level}/${skill.slug}`}>
                  <span className="card__title">{skill.label}</span>
                  <span className="muted">{skill.description}</span>
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}