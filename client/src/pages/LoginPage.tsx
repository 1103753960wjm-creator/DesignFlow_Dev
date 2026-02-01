import { useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { formatApiError } from "@/lib/apiError"
import { setAccessToken } from "@/lib/auth"
import { checkPassword, isValidEmail, normalizeEmail } from "@/lib/validation"
import { login } from "@/features/auth/authApi"

export function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [touchedEmail, setTouchedEmail] = useState(false)
  const [touchedPassword, setTouchedPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const emailOk = useMemo(() => isValidEmail(email), [email])
  const passwordCheck = useMemo(() => checkPassword(password), [password])
  const hasClientError = useMemo(() => !emailOk || !passwordCheck.ok, [emailOk, passwordCheck.ok])

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
            <CardTitle className="text-slate-900">登录 Structura AI</CardTitle>
            <CardDescription>使用邮箱与密码登录，获取 JWT 通行证。</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              onSubmit={async (e) => {
                e.preventDefault()
                setError(null)
                setTouchedEmail(true)
                setTouchedPassword(true)
                if (hasClientError) {
                  setError("请先修正表单错误")
                  return
                }
                setLoading(true)
                try {
                  const res = await login({ email: normalizeEmail(email), password })
                  setAccessToken(res.data.access_token)
                  navigate(next ?? "/app?mode=interior", { replace: true })
                } catch (err: any) {
                  setError(formatApiError(err))
                } finally {
                  setLoading(false)
                }
              }}
            >
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
                <Label htmlFor="password">密码</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onBlur={() => setTouchedPassword(true)}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
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
                {loading ? "登录中..." : "登录"}
              </Button>

              <div className="text-center text-sm text-slate-600">
                还没有账号？{" "}
                <Link
                  to={next ? `/register?next=${encodeURIComponent(next)}` : "/register"}
                  className="font-medium text-indigo-600 hover:text-indigo-700"
                >
                  去注册
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

