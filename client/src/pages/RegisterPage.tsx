import { useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { formatApiError } from "@/lib/apiError"
import { setAccessToken } from "@/lib/auth"
import { checkPassword, isValidEmail, isValidPhone, normalizeEmail, normalizeNickname, normalizePhone } from "@/lib/validation"
import { register } from "@/features/auth/authApi"

export function RegisterPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [nickname, setNickname] = useState("")
  const [email, setEmail] = useState("")
  const [phone, setPhone] = useState("")
  const [password, setPassword] = useState("")
  const [touchedEmail, setTouchedEmail] = useState(false)
  const [touchedPhone, setTouchedPhone] = useState(false)
  const [touchedPassword, setTouchedPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const emailOk = useMemo(() => isValidEmail(email), [email])
  const phoneOk = useMemo(() => isValidPhone(phone), [phone])
  const passwordCheck = useMemo(() => checkPassword(password), [password])
  const nicknameHint = useMemo(() => {
    const v = normalizeNickname(nickname)
    if (!v) return "可选，用于展示"
    if (v.length > 24) return "昵称建议不超过 24 字符"
    return "昵称格式正常"
  }, [nickname])
  const nicknameOk = useMemo(() => normalizeNickname(nickname).length <= 24, [nickname])
  const hasClientError = useMemo(
    () => !emailOk || !passwordCheck.ok || !nicknameOk || !phoneOk,
    [emailOk, passwordCheck.ok, nicknameOk, phoneOk]
  )

  const nextRaw = searchParams.get("next")
  const next =
    nextRaw && nextRaw.startsWith("/")
      ? nextRaw
      : nextRaw
        ? (() => {
            try {
              const decoded = decodeURIComponent(nextRaw)
              return decoded.startsWith("/") ? decoded : null
            } catch {
              return null
            }
          })()
        : null

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-slate-900">注册 Structura AI</CardTitle>
            <CardDescription>创建账号后自动登录。</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              onSubmit={async (e) => {
                e.preventDefault()
                setError(null)
                setTouchedEmail(true)
                setTouchedPhone(true)
                setTouchedPassword(true)
                if (hasClientError) {
                  setError("请先修正表单错误")
                  return
                }
                setLoading(true)
                try {
                  const nick = normalizeNickname(nickname)
                  const p = normalizePhone(phone)
                  const res = await register({
                    nickname: nick || undefined,
                    phone: p,
                    email: normalizeEmail(email),
                    password,
                  })
                  setAccessToken(res.data.access_token)
                  navigate(next ?? "/app?mode=interior", { replace: true })
                } catch (err: unknown) {
                  setError(formatApiError(err))
                } finally {
                  setLoading(false)
                }
              }}
            >
              <div className="space-y-2">
                <Label htmlFor="nickname">昵称</Label>
                <Input
                  id="nickname"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  placeholder="设计师A"
                  aria-invalid={!nicknameOk}
                  aria-describedby="nickname-hint"
                  className={!nicknameOk ? "border-red-300 focus-visible:ring-red-200" : undefined}
                />
                <div id="nickname-hint" className={!nicknameOk ? "text-xs text-red-700" : "text-xs text-slate-500"}>
                  {nicknameHint}
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">邮箱</Label>
                <Input
                  id="email"
                  value={email}
                  onBlur={() => setTouchedEmail(true)}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@studio.com"
                  aria-invalid={touchedEmail && !emailOk}
                  aria-describedby="email-hint"
                  className={touchedEmail && !emailOk ? "border-red-300 focus-visible:ring-red-200" : undefined}
                />
                <div id="email-hint" className={touchedEmail && !emailOk ? "text-xs text-red-700" : "text-xs text-slate-500"}>
                  {touchedEmail && !emailOk ? "请输入正确的邮箱格式" : "用于登录与找回账号"}
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone">手机号</Label>
                <Input
                  id="phone"
                  value={phone}
                  onBlur={() => setTouchedPhone(true)}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="13800138000"
                  inputMode="numeric"
                  aria-invalid={touchedPhone && !phoneOk}
                  aria-describedby="phone-hint"
                  className={touchedPhone && !phoneOk ? "border-red-300 focus-visible:ring-red-200" : undefined}
                />
                <div id="phone-hint" className={touchedPhone && !phoneOk ? "text-xs text-red-700" : "text-xs text-slate-500"}>
                  {touchedPhone && !phoneOk ? "手机号需为 11 位数字" : "用于短信登录/找回账号"}
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">密码</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onBlur={() => setTouchedPassword(true)}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="至少 8 位"
                  aria-invalid={touchedPassword && !passwordCheck.ok}
                  aria-describedby="password-hint"
                  className={touchedPassword && !passwordCheck.ok ? "border-red-300 focus-visible:ring-red-200" : undefined}
                />
                <div
                  id="password-hint"
                  className={touchedPassword && !passwordCheck.ok ? "text-xs text-red-700" : passwordCheck.ok ? "text-xs text-emerald-700" : "text-xs text-slate-500"}
                >
                  {touchedPassword || password ? passwordCheck.message : "至少 8 位"}
                </div>
              </div>

              {error && <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

              <Button type="submit" className="w-full" disabled={loading || hasClientError}>
                {loading ? "注册中..." : "注册并进入"}
              </Button>

              <div className="text-center text-sm text-slate-600">
                已有账号？{" "}
                <Link
                  to={next ? `/login?next=${encodeURIComponent(next)}` : "/login"}
                  className="font-medium text-indigo-600 hover:text-indigo-700"
                >
                  去登录
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

