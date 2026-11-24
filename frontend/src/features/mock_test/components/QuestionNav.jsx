// Phiếu trả lời điện tử (Answer Sheet): hỗ trợ nhóm theo kỹ năng & khóa một chiều chuẩn HSK iBT (`严禁跨区`)
export default function QuestionNav({
  items,
  sections = null,
  mode,
  flags,
  current,
  onSelect = null,
  activeSkill = null,
  lockedSkills = [],
}) {
  function handleJump(no, isLocked = false) {
    if (isLocked) return;
    if (onSelect) {
      onSelect(no);
      return;
    }
    document.getElementById(`q-${no}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function renderBtn(item, isLocked = false) {
    let state = "";
    if (mode === "review") {
      state = item.ket_qua?.dung === true ? " is-ok" : item.ket_qua?.dung === false ? " is-bad" : " is-pending";
    } else if (item.tra_loi?.phuong_an_chon_id || (item.tra_loi?.van_ban || "").trim()) {
      state = " is-done";
    }
    const flagged = flags?.has(item.so_cau);
    return (
      <button
        key={item.so_cau}
        type="button"
        disabled={isLocked}
        className={`xt-nav__btn${state}${flagged ? " is-flag" : ""}${current === item.so_cau ? " is-current" : ""}`}
        onClick={() => handleJump(item.so_cau, isLocked)}
        title={isLocked ? "Phần thi này đang khóa theo quy chế một chiều" : undefined}
        aria-label={`Câu ${item.so_cau}${flagged ? ", đã đánh dấu xem lại" : ""}${isLocked ? ", đang khóa" : ""}`}
      >
        {item.so_cau}
      </button>
    );
  }

  if (sections && sections.length > 0) {
    return (
      <nav className="xt-nav" aria-label={mode === "review" ? "Đối chiếu phiếu trả lời" : "Phiếu trả lời điện tử"}>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {sections.map((sec) => {
            const secItems = items.filter((i) => !i.la_cau_vi_du && i.ky_nang === sec.ky_nang);
            if (!secItems.length) return null;

            if (mode === "review") {
              const okCnt = secItems.filter((i) => i.ket_qua?.dung === true).length;
              return (
                <div key={sec.ky_nang} className="ibt-sheet-sec">
                  <div className="ibt-sheet-sec__title">
                    <span>
                      {sec.title} ({sec.label})
                    </span>
                    <span>
                      {okCnt}/{secItems.length} đạt
                    </span>
                  </div>
                  <div className="xt-nav__grid">{secItems.map((it) => renderBtn(it, false))}</div>
                </div>
              );
            }

            const doneCnt = secItems.filter(
              (i) => i.tra_loi?.phuong_an_chon_id || (i.tra_loi?.van_ban || "").trim()
            ).length;
            const isPastLocked = lockedSkills.includes(sec.ky_nang);
            const isLocked = Boolean(activeSkill && sec.ky_nang !== activeSkill);
            return (
              <div key={sec.ky_nang} className={`ibt-sheet-sec${isLocked ? " is-locked" : ""}`}>
                <div className="ibt-sheet-sec__title">
                  <span>
                    {sec.title} ({sec.label})
                  </span>
                  <span>
                    {isPastLocked
                      ? `🔒 Đã khóa · ${doneCnt}/${secItems.length}`
                      : isLocked
                        ? `🔒 Chưa mở · ${doneCnt}/${secItems.length}`
                        : `● Đang thi · ${doneCnt}/${secItems.length}`}
                  </span>
                </div>
                <div className="xt-nav__grid">{secItems.map((it) => renderBtn(it, isLocked))}</div>
              </div>
            );
          })}
        </div>
      </nav>
    );
  }

  const scored = items.filter((i) => !i.la_cau_vi_du);
  return (
    <nav className="xt-nav" aria-label="Danh sách câu">
      <div className="xt-nav__grid">{scored.map((it) => renderBtn(it, false))}</div>
    </nav>
  );
}
