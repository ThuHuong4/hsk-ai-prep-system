import { ADMIN_MENU } from "../shared/navigation/roleMenus.js";
import StaffLayout from "./StaffLayout.jsx";

// Cùng giao diện thanh bên với Giảng viên (bản mô phỏng), chế độ Sáng/Tối
export default function AdminLayout() {
  return <StaffLayout roleLabel="Quản trị viên" menu={ADMIN_MENU} />;
}
