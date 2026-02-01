export function normalizeEmail(email: string): string {
  return email.trim()
}

export function isValidEmail(email: string): boolean {
  const v = normalizeEmail(email)
  if (!v) return false
  if (v.length > 254) return false
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)
}

export function normalizeNickname(nickname: string): string {
  return nickname.trim()
}

export function normalizePhone(phone: string): string {
  return phone.trim().replace(/[^\d]/g, "")
}

export function isValidPhone(phone: string): boolean {
  const v = normalizePhone(phone)
  return /^\d{11}$/.test(v)
}

export type PasswordCheck = {
  ok: boolean
  message: string
}

export function checkPassword(password: string): PasswordCheck {
  if (!password) return { ok: false, message: "请输入密码" }
  if (password.length < 8) return { ok: false, message: `密码至少 8 位（当前 ${password.length} 位）` }
  return { ok: true, message: "密码长度符合要求" }
}

