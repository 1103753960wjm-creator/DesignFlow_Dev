import { useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"

export function WorkshopPage() {
  const navigate = useNavigate()

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <div className="text-2xl font-semibold text-slate-900">设计工坊</div>
        <div className="text-sm text-slate-600">选择一个工作流开始创作（当前室内已接入 Mock 全链路）。</div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="text-lg font-semibold text-slate-900">室内设计</div>
          <div className="mt-2 text-sm text-slate-600">上传 CAD → DXF 预览 → 白模/画廊（Mock）</div>
          <Button className="mt-5" onClick={() => navigate("/app/interior?mode=interior")}>
            进入
          </Button>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="text-lg font-semibold text-slate-900">景观</div>
          <div className="mt-2 text-sm text-slate-600">结构约束下的场景一致输出（占位）</div>
          <Button variant="secondary" className="mt-5" disabled>
            即将上线
          </Button>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="text-lg font-semibold text-slate-900">平面海报</div>
          <div className="mt-2 text-sm text-slate-600">多风格快速出图与模板复用（占位）</div>
          <Button variant="secondary" className="mt-5" disabled>
            即将上线
          </Button>
        </div>
      </div>
    </div>
  )
}

