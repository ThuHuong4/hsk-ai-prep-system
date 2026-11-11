import { STUDENT_MENU } from "../shared/navigation/roleMenus.js";
import RoleLayout from "./RoleLayout.jsx";

export default function StudentLayout() {
  return <RoleLayout roleLabel="Học viên" menu={STUDENT_MENU} variant="tabs" />;
}