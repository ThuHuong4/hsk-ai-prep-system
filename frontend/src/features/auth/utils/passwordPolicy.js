export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;

// Khớp app/security/password_policy.py; backend vẫn kiểm tra lại
export function validatePassword(password) {
  if (password.length < PASSWORD_MIN_LENGTH || password.length > PASSWORD_MAX_LENGTH) {
    return `Mật khẩu phải từ ${PASSWORD_MIN_LENGTH} đến ${PASSWORD_MAX_LENGTH} ký tự`;
  }
  if (!/\p{L}/u.test(password) || !/\d/.test(password)) {
    return "Mật khẩu phải có ít nhất 1 chữ cái và 1 chữ số";
  }
  return "";
}