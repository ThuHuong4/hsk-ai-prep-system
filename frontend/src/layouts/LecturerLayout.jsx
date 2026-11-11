import { LECTURER_MENU } from "../shared/navigation/roleMenus.js";
import RoleLayout from "./RoleLayout.jsx";

export default function LecturerLayout() {
  return <RoleLayout roleLabel="Giảng viên" menu={LECTURER_MENU} />;
}