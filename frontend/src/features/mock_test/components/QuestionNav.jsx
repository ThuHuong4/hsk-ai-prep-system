// Lưới số câu: bấm để cuộn tới câu; đánh dấu câu đã làm (hoặc đúng/sai khi xem lại); 🚩 = câu đánh dấu xem lại
export default function QuestionNav({ items, mode, flags, current }) {
  const scored = items.filter((i) => !i.la_cau_vi_du);
  function go(no) {
    document.getElementById(`q-${no}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  return (
    <nav className="xt-nav" aria-label="Danh sách câu">
      <div className="xt-nav__grid">
        {scored.map((item) => {
          let state = "";
          if (mode === "review") state = item.ket_qua?.dung === true ? " is-ok" : item.ket_qua?.dung === false ? " is-bad" : " is-pending";
          else if (item.tra_loi?.phuong_an_chon_id || item.tra_loi?.van_ban) state = " is-done";
          const flagged = flags?.has(item.so_cau);
          return (
            <button key={item.so_cau} type="button"
              className={`xt-nav__btn${state}${flagged ? " is-flag" : ""}${current === item.so_cau ? " is-current" : ""}`}
              onClick={() => go(item.so_cau)}
              aria-label={`Câu ${item.so_cau}${flagged ? ", đã đánh dấu xem lại" : ""}`}>{item.so_cau}</button>
          );
        })}
      </div>
    </nav>
  );
}
