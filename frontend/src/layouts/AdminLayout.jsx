import { ADMIN_MENU } from "../shared/navigation/roleMenus.js";
import RoleLayout from "./RoleLayout.jsx";

export default function AdminLayout() {
  return <RoleLayout roleLabel="Quản trị viên" menu={ADMIN_MENU} />;
}