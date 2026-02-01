import { useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getAccessToken } from "@/lib/auth"

type Mode = "interior" | "landscape" | "poster"

export function LandingPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>("interior")

  const modeLabel = useMemo(() => {
    if (mode === "interior") return "室内设计"
    if (mode === "landscape") return "景观"
    return "海报"
  }, [mode])

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-2xl bg-indigo-600" />
            <div className="leading-tight">
              <div className="text-sm font-semibold text-slate-900">Structura AI</div>
              <div className="text-xs text-slate-500">结构锁定 · 真·三维 · 多维输出</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => navigate("/login")}>
              登录
            </Button>
            <Button variant="outline" onClick={() => navigate("/register")}>
              注册
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-6">
            <div className="space-y-3">
              <h1 className="text-3xl font-semibold leading-tight text-slate-900 md:text-4xl">
                面向专业设计师的垂直领域智能设计平台
              </h1>
              <p className="max-w-2xl text-sm leading-6 text-slate-600">
                从 CAD 解析生成 3D 白模（Whitebox），再用深度图约束实现多机位、高一致性渲染。
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">结构锁定</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-slate-600">
                  用几何与深度约束绑定结构，减少“漂移”和“乱改”。
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">真·三维</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-slate-600">
                  白模与相机可控，多视角一致输出更接近设计生产流程。
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">多维输出</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-slate-600">
                  支持多机位画廊、可回溯参数与自然语言精修。
                </CardContent>
              </Card>
            </div>
          </div>

          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="text-lg">选择模式</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-2">
                <Button variant={mode === "interior" ? "default" : "secondary"} onClick={() => setMode("interior")}>
                  室内
                </Button>
                <Button variant={mode === "landscape" ? "default" : "secondary"} onClick={() => setMode("landscape")}>
                  景观
                </Button>
                <Button variant={mode === "poster" ? "default" : "secondary"} onClick={() => setMode("poster")}>
                  海报
                </Button>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                当前模式：<span className="font-medium text-slate-900">{modeLabel}</span>
              </div>

              <Button
                className="w-full"
                onClick={() => {
                  const next = `/app?mode=${mode}`
                  const token = getAccessToken()
                  navigate(token ? next : `/login?next=${encodeURIComponent(next)}`)
                }}
              >
                快速开始
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}

