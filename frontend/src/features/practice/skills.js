export const PRACTICE_SKILLS = [
  { slug: "nghe", label: "Nghe", description: "Nhận biết thông tin qua audio." },
  { slug: "doc", label: "Đọc", description: "Hiểu câu và đoạn văn." },
  { slug: "tu-vung", label: "Từ vựng", description: "Nhận diện và sử dụng từ." },
  { slug: "viet", label: "Viết", description: "Sắp xếp từ, viết chữ và câu.", minLevel: 3 },
];

export function findSkill(slug) {
  return PRACTICE_SKILLS.find((skill) => skill.slug === slug) ?? null;
}