import { HttpError, http } from "../../../shared/api/httpClient.js";

// Mục 6.2: lần đầu tạo gợi ý (AI một lần) rồi lưu; lần sau trả bản đã lưu
export const getRoadmap = (token, luotId) => http.post(`/api/thi-thu/luot/${luotId}/goi-y-lo-trinh`, undefined, { token });

// Tài liệu đang đăng lưu riêng, cần đăng nhập: tải dạng blob rồi tạo URL tạm để xem
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
