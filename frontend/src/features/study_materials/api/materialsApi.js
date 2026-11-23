import { HttpError, http } from "../../../shared/api/httpClient.js";

export const listMaterials = (token, signal) => http.get("/api/tai-lieu", { token, signal });
export const listExternal = (token, signal) => http.get("/api/tai-lieu/lien-ket", { token, signal });

// Tài liệu đang đăng lưu riêng, cần đăng nhập: tải dạng blob kèm token rồi tạo URL tạm để xem
export async function fetchMaterialUrl(token, id) {
  let response;
  try {
    response = await fetch(`/api/tai-lieu/${id}/tep`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    throw new HttpError(0, "Không kết nối được máy chủ");
  }
  if (!response.ok) throw new HttpError(response.status, "Không mở được tài liệu");
  return URL.createObjectURL(await response.blob());
}
