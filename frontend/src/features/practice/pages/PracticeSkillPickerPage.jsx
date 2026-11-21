import { Link, useParams } from "react-router-dom";

import Icon from "../../../shared/components/Icon.jsx";
import "../../exam_catalog/styles/catalog.css";
import { ZH_NUM, levelClass } from "../../exam_catalog/utils/display.js";
import { parseLevelId } from "../../exam_catalog/utils/levels.js";
import { PRACTICE_SKILLS } from "../skills.js";

const SKILL_HZ = { nghe: "听", doc: "读", viet: "写", "tu-vung": "词" };

export default function PracticeSkillPickerPage({ basePath }) {
  const { maCapDo } = useParams();
  const level = parseLevelId(maCapDo);

  if (!level) {
    return (
      <section className="xc">
        <Link className="xc-back" to={basePath}><Icon name="arrowLeft" />Chọn cấp</Link>
        <p role="alert">Cấp độ không hợp lệ.</p>
      </section>
    );
  }

  return (
    <section className="xc">
      <Link className="xc-back" to={basePath}><Icon name="arrowLeft" />Chọn cấp khác</Link>
      <header className={`xc-title ${levelClass(level)}`}>
        <span className="xc-tile xc-tile--lg" aria-hidden="true">{ZH_NUM[level]}</span>
        <span>
          <h1>Ôn luyện HSK {level}</h1>
          <p>Mỗi kỹ năng có tiến độ riêng. Chọn kỹ năng muốn luyện.</p>
        </span>
      </header>
      <ul className="xc-skills">
        {PRACTICE_SKILLS.map((skill) => {
          const locked = skill.minLevel && level < skill.minLevel;
          const body = (
            <>
              <span className="xc-tile xc-tile--lg" aria-hidden="true">{SKILL_HZ[skill.slug]}</span>
              <span className="xc-skill__body">
                <h2>{skill.label}</h2>
                <p>{locked ? `Nội dung Viết áp dụng từ HSK ${skill.minLevel}` : skill.description}</p>
              </span>
            </>
          );
          return (
            <li key={skill.slug}>
              {locked ? (
                <div className={`xc-skill sk-${skill.slug}`} aria-disabled="true">{body}</div>
              ) : (
                <Link className={`xc-skill sk-${skill.slug}`} to={`${basePath}/hsk/${level}/${skill.slug}`}>{body}</Link>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
