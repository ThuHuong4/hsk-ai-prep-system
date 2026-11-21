// Người soạn (bản đầu) và người sửa bản đang hiển thị, lấy từ nguoi_tao_id
export default function CreatorTag({ creator, editor }) {
  if (!creator && !editor) return null;
  return (
    <span className="lv-creator">
      Soạn: {creator || editor}
      {editor && creator && editor !== creator && ` · sửa: ${editor}`}
    </span>
  );
}
