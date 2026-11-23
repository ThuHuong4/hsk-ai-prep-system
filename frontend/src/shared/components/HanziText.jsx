// Chữ Hán có pinyin phía trên. Quy ước: chữ Hán tách từ bằng dấu cách, pinyin tách tương ứng;
// "_" = từ đó không có pinyin. Số từ không khớp → hiện pinyin thành một dòng phía trên.
const BLANK = "（　）";

// Chỗ trống "（　）" hiện thành gạch dưới như đề giấy
function withBlanks(word) {
  if (!word.includes(BLANK)) return word;
  return word.split(BLANK).flatMap((part, i) => (i ? [<span key={i} className="hz-blank" aria-label="chỗ trống" />, part] : [part]));
}

export default function HanziText({ text, pinyin, className = "" }) {
  if (!text) return null;
  const lines = text.split("\n");
  const pyLines = pinyin ? pinyin.split("\n") : [];
  return (
    <span className={`hz ${className}`}>
      {lines.map((line, i) => {
        const words = line.split(" ").filter(Boolean);
        const pys = pyLines[i] ? pyLines[i].split(" ").filter(Boolean) : [];
        if (pys.length && pys.length === words.length) {
          return (
            <span className="hz-line" key={i}>
              {words.map((w, j) => (
                <ruby key={j}>{withBlanks(w)}<rt>{pys[j] === "_" ? "" : pys[j]}</rt></ruby>
              ))}
            </span>
          );
        }
        return (
          <span className="hz-line hz-line--stack" key={i}>
            {pyLines[i] && <span className="hz-py">{pyLines[i].replace(/(^|\s)_(?=\s|$)/g, " ")}</span>}
            <span>{withBlanks(words.join(""))}</span>
          </span>
        );
      })}
    </span>
  );
}
