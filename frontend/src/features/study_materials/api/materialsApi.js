import { http } from "../../../shared/api/httpClient.js";

export { fetchMaterialUrl } from "../../mock_test/api/roadmapApi.js"; // tệp lưu riêng: tải blob kèm token rồi tạo URL tạm

export const listMaterials = (token, signal) => http.get("/api/tai-lieu", { token, signal });
export const listExternal = (token, signal) => http.get("/api/tai-lieu/lien-ket", { token, signal });
