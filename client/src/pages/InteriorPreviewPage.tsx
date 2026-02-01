import { Component, type ReactNode, useEffect, useMemo } from "react"

import { ModelViewer } from "@/components/design/ModelViewer"

class PreviewErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full w-full items-center justify-center bg-slate-950 px-6 text-center">
          <div className="space-y-3">
            <div className="text-sm font-semibold text-white/90">模型解析失败</div>
            <button
              type="button"
              className="inline-flex h-10 items-center justify-center rounded-xl bg-white/10 px-4 text-sm font-semibold text-white hover:bg-white/15"
              onClick={() => window.location.reload()}
            >
              重试
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export function InteriorPreviewPage() {
  const { modelUrl, depthUrl } = useMemo(() => {
    const params = new URLSearchParams(window.location.search)
    return {
      modelUrl: params.get("model") || "",
      depthUrl: params.get("depth") || "",
    }
  }, [])

  useEffect(() => {
    const prevMargin = document.body.style.margin
    const prevOverflow = document.body.style.overflow
    document.body.style.margin = "0"
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.margin = prevMargin
      document.body.style.overflow = prevOverflow
    }
  }, [])

  if (!modelUrl) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-950 text-sm text-white/70">缺少模型地址</div>
  }

  return (
    <div className="h-screen overflow-hidden bg-slate-950">
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <div className="text-sm font-semibold text-white/90">3D 白模预览</div>
        <div className="flex items-center gap-2">
          <a
            href={modelUrl}
            download
            className="inline-flex h-9 items-center justify-center rounded-xl bg-white/10 px-3 text-xs font-semibold text-white hover:bg-white/15"
          >
            下载白模
          </a>
          {depthUrl && (
            <a
              href={depthUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-9 items-center justify-center rounded-xl bg-white/10 px-3 text-xs font-semibold text-white hover:bg-white/15"
            >
              查看深度
            </a>
          )}
        </div>
      </div>

      <div className="h-[calc(100vh-56px)] w-full overflow-hidden">
        <PreviewErrorBoundary>
          <ModelViewer url={modelUrl} className="h-full w-full" />
        </PreviewErrorBoundary>
      </div>
    </div>
  )
}

