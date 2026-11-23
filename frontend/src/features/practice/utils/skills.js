export const PRACTICE_SKILLS = [
  { slug: "nghe", label: "Nghe", description: "Nhận biết thông tin qua audio." },
  { slug: "doc", label: "Đọc", description: "Hiểu câu và đoạn văn." },
  { slug: "viet", label: "Viết", description: "Sắp xếp từ, viết chữ và câu.", minLevel: 3 },
  { slug: "tu-vung", label: "Từ vựng", description: "Nhận diện và sử dụng từ." },
];

// Mã kỹ năng phía máy chủ (tu_vung) ↔ đường dẫn (tu-vung); chữ Hán trên ô kỹ năng
export const skillApi = (slug) => slug.replace("-", "_");
export const skillSlug = (api) => api.replace("_", "-");
export const SKILL_HZ = { nghe: "听", doc: "读", viet: "写", "tu-vung": "词" };

export function findSkill(slug) {
  return PRACTICE_SKILLS.find((skill) => skill.slug === slug) ?? null;
}
