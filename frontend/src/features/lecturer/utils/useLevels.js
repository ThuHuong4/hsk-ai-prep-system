import { useAuth } from "../../auth/context/AuthContext.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { listLevelsAdmin } from "../api/lecturerApi.js";

// Giảng viên thấy mọi cấp (kể cả nháp) để soạn nội dung trước; trả dạng { ma_cap_do, ten_cap_do } như trước
export function useLevels() {
  const { token } = useAuth();
  const { data } = useRequest((signal) => listLevelsAdmin(token, signal), [token]);
  return (data || []).filter((l) => l.trang_thai !== "da_an").map((l) => ({ ma_cap_do: l.id, ten_cap_do: l.ten, trang_thai: l.trang_thai }));
}
