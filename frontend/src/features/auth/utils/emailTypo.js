// Gợi ý khi gõ nhầm tên miền email phổ biến (vd: gmaill.com → gmail.com)
const COMMON_DOMAINS = [
  "gmail.com", "yahoo.com", "yahoo.com.vn", "outlook.com", "hotmail.com",
  "icloud.com", "live.com", "msn.com",
];

function distance(a, b) {
  const dp = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j += 1) dp[0][j] = j;
  for (let i = 1; i <= a.length; i += 1) {
    for (let j = 1; j <= b.length; j += 1) {
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,
        dp[i][j - 1] + 1,
        dp[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
    }
  }
  return dp[a.length][b.length];
}

// Trả email đã sửa, hoặc null nếu không nghi gõ nhầm
export function suggestEmail(email) {
  const at = email.lastIndexOf("@");
  if (at < 1) return null;
  const domain = email.slice(at + 1).toLowerCase();
  if (!domain || COMMON_DOMAINS.includes(domain)) return null;
  let best = null;
  let bestDist = 3;
  for (const candidate of COMMON_DOMAINS) {
    const d = distance(domain, candidate);
    if (d > 0 && d < bestDist) {
      best = candidate;
      bestDist = d;
    }
  }
  return best ? `${email.slice(0, at)}@${best}` : null;
}
