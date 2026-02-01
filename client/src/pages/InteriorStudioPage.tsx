import { useEffect, useMemo, useRef, useState } from "react"

import { type UploadResult } from "@/ImageUploader"
import { CadPreview } from "@/components/cad/CadPreview"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { formatApiError } from "@/lib/apiError"

type WhiteboxResponse = {
  whitebox_url: string
  depth_url: string
}

type GalleryResponse = {
  images: string[]
}

type ProcessCadResponse = {
  task_id: string
  status: "processing" | "done"
  output_dir?: string | null
  model_obj_url?: string | null
  depth_urls?: Record<string, string> | null
}

type TaskStatusResponse = {
  task_id: string
  status: string
  progress?: number
  assets?: { model_obj_url: string; depth_urls: Record<string, string> }
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V7" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.5 10.5 12 7l3.5 3.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 17.5A3.5 3.5 0 0 0 7.5 21h9A3.5 3.5 0 0 0 20 17.5" />
    </svg>
  )
}

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-7H10v7H5a1 1 0 0 1-1-1v-9.5Z" />
    </svg>
  )
}

function TreeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v18" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5c-3 2-5 4-6 7 3-1 5 0 6 2 1-2 3-3 6-2-1-3-3-5-6-7Z" />
    </svg>
  )
}

function MonitorIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 5h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 21h8" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v3" />
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v5l3 2" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z" />
    </svg>
  )
}

function BoltIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 2 3 14h7l-1 8 12-14h-7l-1-6Z" />
    </svg>
  )
}

function CubeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3 4 7.5v9L12 21l8-4.5v-9L12 3Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v18" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7.5 12 12l8-4.5" />
    </svg>
  )
}

export function InteriorStudioPage() {
  const [uploaded, setUploaded] = useState<UploadResult | null>(null)
  const [whitebox, setWhitebox] = useState<WhiteboxResponse | null>(null)
  const [gallery, setGallery] = useState<string[] | null>(null)
  const [galleryViews, setGalleryViews] = useState<Array<"main" | "side" | "topA"> | null>(null)
  const [resultIndex, setResultIndex] = useState(0)
  const [refineText, setRefineText] = useState("")
  const [cadDepthUrls, setCadDepthUrls] = useState<Record<string, string> | null>(null)
  const [processingText, setProcessingText] = useState<string | null>(null)
  const [styleKey, setStyleKey] = useState<"modern" | "wabi" | "custom">("modern")
  const [customPrompt, setCustomPrompt] = useState("")
  const [controlStrength, setControlStrength] = useState(0.7)
  const [loadingWhitebox, setLoadingWhitebox] = useState(false)
  const [loadingGallery, setLoadingGallery] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [cameraMain, setCameraMain] = useState(true)
  const [cameraSide, setCameraSide] = useState(true)
  const [cameraTop, setCameraTop] = useState(false)

  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const noticeTimerRef = useRef<number | null>(null)
  const pollTimerRef = useRef<number | null>(null)

  const isDxf = useMemo(() => (uploaded ? uploaded.file.name.toLowerCase().endsWith(".dxf") : false), [uploaded])
  const currentStep = useMemo(() => {
    if (!uploaded) return 1
    if (!whitebox) return 2
    return 3
  }, [uploaded, whitebox])

  const selectedStyleLabel = useMemo(() => {
    if (styleKey === "modern") return "现代简约"
    if (styleKey === "wabi") return "侘寂风"
    return "自定义风格"
  }, [styleKey])

  const resolvedPrompt = useMemo(() => {
    const base = styleKey === "modern" ? "现代简约" : styleKey === "wabi" ? "侘寂风" : ""
    const extra = customPrompt.trim()
    return [base, "室内设计", extra].filter(Boolean).join("，")
  }, [customPrompt, styleKey])

  useEffect(() => {
    if (!gallery?.length) return
    setResultIndex(0)
  }, [gallery])

  const currentViewLabel = useMemo(() => {
    const key = galleryViews?.[resultIndex]
    if (key === "side") return "俯视图 (Top)"
    if (key === "topA") return "立面A (Elevation)"
    return "主视角 (Main)"
  }, [galleryViews, resultIndex])

  const currentResultUrl = useMemo(() => {
    if (!gallery?.length) return null
    const idx = Math.min(Math.max(resultIndex, 0), gallery.length - 1)
    return gallery[idx]
  }, [gallery, resultIndex])

  async function uploadFile(file: File) {
    const previewUrl = URL.createObjectURL(file)
    setUploading(true)
    setError(null)
    setUploaded(null)
    setWhitebox(null)
    setGallery(null)
    setGalleryViews(null)
    setCadDepthUrls(null)
    setProcessingText(null)
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }

    const formData = new FormData()
    formData.append("file", file)

    try {
      const ext = file.name.toLowerCase()
      if (ext.endsWith(".dxf")) {
        setProcessingText("AI 正在解析 CAD 结构...")
        setUploaded({ file, previewUrl, filename: file.name, url: "", encrypted: true })

        const res = await api.post<ProcessCadResponse>("/design/process-cad", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        })
        const taskId = res.data.task_id

        if (res.data.status === "done" && res.data.model_obj_url && res.data.depth_urls) {
          setCadDepthUrls(res.data.depth_urls)
          setWhitebox({
            whitebox_url: res.data.model_obj_url,
            depth_url: res.data.depth_urls["0"] || res.data.depth_urls["main"] || res.data.depth_urls["top"] || "",
          })
          setProcessingText(null)
          return
        }

        pollTimerRef.current = window.setInterval(async () => {
          try {
            const st = await api.get<TaskStatusResponse>(`/tasks/${taskId}`)
            if (st.data.status === "FAILURE") {
              setError("CAD 处理失败")
              setProcessingText(null)
              if (pollTimerRef.current) window.clearInterval(pollTimerRef.current)
              pollTimerRef.current = null
              return
            }
            if (typeof st.data.progress === "number") {
              setProcessingText(`正在生成三维白模... ${st.data.progress}%`)
            } else {
              setProcessingText("正在生成三维白模...")
            }
            if (st.data.status === "SUCCESS" && st.data.assets?.model_obj_url) {
              setCadDepthUrls(st.data.assets.depth_urls)
              setWhitebox({
                whitebox_url: st.data.assets.model_obj_url,
                depth_url: st.data.assets.depth_urls["0"] || st.data.assets.depth_urls["main"] || st.data.assets.depth_urls["top"] || "",
              })
              setProcessingText(null)
              if (pollTimerRef.current) window.clearInterval(pollTimerRef.current)
              pollTimerRef.current = null
            }
          } catch {
            setProcessingText("正在生成三维白模...")
          }
        }, 2000)
      } else {
        const res = await api.post("/design/upload", formData, { headers: { "Content-Type": "multipart/form-data" } })
        const filename = res.data.filename as string
        const url = res.data.url as string
        const encrypted = res.data.encrypted as boolean | undefined
        setUploaded({ file, previewUrl, filename, url, encrypted })
      }
    } catch (err: any) {
      setError(formatApiError(err))
    } finally {
      setUploading(false)
    }
  }

  useEffect(() => {
    return () => {
      if (noticeTimerRef.current) window.clearTimeout(noticeTimerRef.current)
      if (pollTimerRef.current) window.clearInterval(pollTimerRef.current)
    }
  }, [])

  function showComingSoon(label: string) {
    setNotice(`${label}功能即将上线`)
    if (noticeTimerRef.current) window.clearTimeout(noticeTimerRef.current)
    noticeTimerRef.current = window.setTimeout(() => setNotice(null), 2500)
  }

  async function ensureWhitebox() {
    if (!uploaded) return null
    if (whitebox) return whitebox
    const res = await api.post<WhiteboxResponse>("/design/whitebox", {
      filename: uploaded.filename,
      source_url: uploaded.url,
    })
    setWhitebox(res.data)
    return res.data
  }

  async function generateWhitebox() {
    if (!uploaded) return
    setError(null)
    setGallery(null)
    setGalleryViews(null)
    setLoadingWhitebox(true)
    try {
      await ensureWhitebox()
    } catch (err: any) {
      setError(formatApiError(err))
    } finally {
      setLoadingWhitebox(false)
    }
  }

  async function startBatchRender() {
    if (!uploaded || !whitebox) return
    const selectedViews: Array<"main" | "side" | "topA"> = []
    if (cameraMain) selectedViews.push("main")
    if (cameraSide) selectedViews.push("side")
    if (cameraTop) selectedViews.push("topA")
    if (!selectedViews.length) {
      setError("请至少选择一个机位")
      return
    }

    setError(null)
    setLoadingGallery(true)
    try {
      const res = await api.post<GalleryResponse>("/design/gallery", {
        whitebox_url: whitebox.whitebox_url,
        depth_url: whitebox.depth_url,
        prompt: resolvedPrompt,
        strength: controlStrength,
        cameras: { main: cameraMain, side: cameraSide, topA: cameraTop },
      })
      const images = res.data.images
      setGallery(images)
      setGalleryViews(images.map((_, idx) => selectedViews[idx % selectedViews.length]))
    } catch (err: any) {
      setError(formatApiError(err))
    } finally {
      setLoadingGallery(false)
    }
  }

  function downloadCurrentImage() {
    if (!currentResultUrl) return
    const a = document.createElement("a")
    a.href = currentResultUrl
    a.download = `render-${resultIndex + 1}.png`
    a.rel = "noreferrer"
    document.body.appendChild(a)
    a.click()
    a.remove()
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="inline-flex items-center gap-1 rounded-2xl border border-slate-200 bg-white p-1 shadow-sm">
          <a
            href="/app/interior?mode=interior"
            className="inline-flex h-10 items-center gap-2 rounded-xl bg-indigo-600 px-4 text-sm font-medium text-white"
          >
            <HomeIcon />
            室内设计
          </a>
          <button
            type="button"
            className="inline-flex h-10 items-center gap-2 rounded-xl px-4 text-sm font-medium text-slate-700 hover:bg-slate-100"
            onClick={() => showComingSoon("景观设计")}
          >
            <TreeIcon />
            景观设计
          </button>
          <button
            type="button"
            className="inline-flex h-10 items-center gap-2 rounded-xl px-4 text-sm font-medium text-slate-700 hover:bg-slate-100"
            onClick={() => showComingSoon("海报设计")}
          >
            <MonitorIcon />
            海报设计
          </button>
        </div>

        <div className="flex items-center justify-between gap-3">
          <div className="hidden items-center gap-2 text-sm md:flex">
            <span className={currentStep === 1 ? "font-semibold text-indigo-600" : "text-slate-400"}>1. 导入</span>
            <span className="text-slate-300">›</span>
            <span className={currentStep === 2 ? "font-semibold text-indigo-600" : "text-slate-400"}>2. 配置</span>
            <span className="text-slate-300">›</span>
            <span className={currentStep === 3 ? "font-semibold text-indigo-600" : "text-slate-400"}>3. 生成</span>
          </div>
          <Button variant="outline" className="rounded-xl" disabled>
            <ClockIcon />
            历史记录
          </Button>
        </div>
      </div>

      {notice && <div className="rounded-2xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-700">{notice}</div>}
      {processingText && (
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm">
          {processingText}
        </div>
      )}

      {!uploaded ? (
        <div className="rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="m-4 flex min-h-[560px] items-center justify-center rounded-3xl border-2 border-dashed border-slate-200 bg-slate-50">
            <div className="max-w-md text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-indigo-100/70 text-indigo-600">
                <UploadIcon />
              </div>
              <div className="mt-6 text-xl font-semibold text-slate-900">上传 室内CAD / 户型图</div>
              <div className="mt-3 text-sm text-slate-600">
                当前模式：<span className="font-medium text-indigo-600">室内设计</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">结构锁定，精准施工图还原</div>

              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".jpg,.png,.jpeg,.dxf,.dwg"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (!file) return
                  uploadFile(file)
                }}
              />

              <Button
                variant="outline"
                className="mt-7 h-11 rounded-xl bg-white px-8 shadow-sm"
                disabled={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading ? "上传中..." : "选择文件"}
              </Button>

              {error && <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.35fr_0.65fr]">
          <div className="rounded-3xl border border-slate-200 bg-[#0b1220] shadow-sm">
            <div className="flex items-center justify-between px-5 pt-5">
              <div className="flex flex-wrap gap-2">
                <div className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-3 py-2 text-xs font-medium text-white">
                  <CubeIcon />
                  结构锁定：3D WHITEBOX
                </div>
                <div className="inline-flex items-center gap-2 rounded-xl bg-indigo-600/80 px-3 py-2 text-xs font-medium text-white">
                  <BoltIcon />
                  {whitebox ? "已生成白模（Auto-Modeling）" : "等待生成白模（Auto-Modeling）"}
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                className="rounded-xl bg-white/5 text-white hover:bg-white/10"
                onClick={() => {
                  setUploaded(null)
                  setWhitebox(null)
                  setGallery(null)
                  setError(null)
                }}
              >
                重新导入
              </Button>
            </div>

            <div className="px-5 pb-5 pt-3">
              <div className="min-h-[600px] rounded-3xl bg-gradient-to-b from-white/5 to-white/0">
                <div className="h-[600px] w-full">
                  <div className="mx-auto w-full overflow-hidden rounded-2xl border border-white/10 bg-white/5">
                    {!whitebox ? (
                      isDxf ? (
                        <div className="p-4">
                          <div className="mb-3 text-left text-xs text-white/50">导入预览（DXF 轻预览）</div>
                          <div className="overflow-hidden rounded-xl bg-white">
                            <CadPreview file={uploaded.file} />
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-2 p-6 text-center text-sm text-white/60">
                          <div className="text-xs text-white/50">已导入素材：{uploaded.filename}</div>
                          <img src={uploaded.previewUrl} alt="Preview" className="mx-auto h-56 w-[420px] rounded-xl object-cover" />
                        </div>
                      )
                    ) : (
                      <div className="h-[600px] w-full">
                        <iframe
                          title="whitebox-preview"
                          src={`/interior-preview?model=${encodeURIComponent(whitebox.whitebox_url)}&depth=${encodeURIComponent(
                            whitebox.depth_url,
                          )}`}
                          className="h-[600px] w-full"
                          scrolling="no"
                        />
                      </div>
                    )}
                  </div>

                  <div className="mt-3 text-center text-xs text-white/40">
                    [ 3D 白模预览区 ] 可拖拽旋转视角 · 已自动拉伸墙体高度 2.8m
                  </div>
                </div>
              </div>

              <div className="mt-5 rounded-2xl bg-white/5 px-4 py-3">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="text-sm font-medium text-white/80">虚拟拍摄机位</div>
                  <div className="flex items-center gap-3 text-xs text-white/70">
                    <label className="inline-flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={cameraMain}
                        disabled={!whitebox}
                        onChange={(e) => setCameraMain(e.target.checked)}
                      />
                      主视角
                    </label>
                    <label className="inline-flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={cameraSide}
                        disabled={!whitebox}
                        onChange={(e) => setCameraSide(e.target.checked)}
                      />
                      俯视图
                    </label>
                    <label className="inline-flex items-center gap-2">
                      <input type="checkbox" checked={cameraTop} disabled={!whitebox} onChange={(e) => setCameraTop(e.target.checked)} />
                      立面A
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="text-lg font-semibold text-slate-900">生成配置（室内设计）</div>

            <div className="mt-6 space-y-3">
              <div className="text-sm font-medium text-slate-900">选择风格流派</div>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setStyleKey("modern")}
                  className={`rounded-2xl border p-3 text-left transition-colors ${
                    styleKey === "modern" ? "border-indigo-200 bg-indigo-50" : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <div className="h-16 w-full rounded-xl bg-gradient-to-br from-slate-100 to-slate-200" />
                  <div className="mt-2 text-sm font-semibold text-slate-900">现代简约</div>
                </button>
                <button
                  type="button"
                  onClick={() => setStyleKey("wabi")}
                  className={`rounded-2xl border p-3 text-left transition-colors ${
                    styleKey === "wabi" ? "border-indigo-200 bg-indigo-50" : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <div className="h-16 w-full rounded-xl bg-gradient-to-br from-stone-100 to-stone-200" />
                  <div className="mt-2 text-sm font-semibold text-slate-900">侘寂风</div>
                </button>
                <button
                  type="button"
                  onClick={() => setStyleKey("custom")}
                  className={`col-span-2 rounded-2xl border border-dashed p-4 text-left transition-colors ${
                    styleKey === "custom" ? "border-indigo-200 bg-indigo-50" : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <div className="inline-flex items-center gap-2 text-sm font-semibold text-slate-900">
                    <BoltIcon />
                    自定义风格
                  </div>
                  <div className="mt-1 text-xs text-slate-500">支持参考图</div>
                </button>
              </div>

              {styleKey === "custom" && (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <div className="text-xs font-medium text-slate-700">自定义描述</div>
                  <textarea
                    value={customPrompt}
                    onChange={(e) => setCustomPrompt(e.target.value)}
                    rows={3}
                    className="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-200"
                    placeholder="例如：奶油风、柔光、木质材质、浅色墙面、温馨客厅..."
                  />
                </div>
              )}
            </div>

            <div className="mt-6 space-y-3">
              <div className="text-sm font-medium text-slate-900">模型参数</div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-600">
                  <div>结构锁定强度 (ControlNet)</div>
                  <div className="font-medium text-slate-900">{controlStrength.toFixed(1)}</div>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={controlStrength}
                  onChange={(e) => setControlStrength(Number(e.target.value))}
                  className="w-full accent-indigo-600"
                />
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-indigo-100 bg-indigo-50 px-4 py-3">
              <div className="text-sm font-medium text-indigo-800">知识库联动</div>
              <div className="mt-1 text-xs text-indigo-700">已加载施工规范文档库。</div>
            </div>

            {error && <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

            {isDxf ? (
              <Button className="mt-6 h-12 w-full rounded-2xl" disabled>
                <CubeIcon />
                {whitebox ? "白模已生成" : "CAD 处理中..."}
              </Button>
            ) : !whitebox ? (
              <Button className="mt-6 h-12 w-full rounded-2xl" disabled={loadingWhitebox || uploading} onClick={generateWhitebox}>
                <CubeIcon />
                {loadingWhitebox ? "生成白模中..." : "生成白模"}
              </Button>
            ) : (
              <Button className="mt-6 h-12 w-full rounded-2xl" disabled={loadingGallery} onClick={startBatchRender}>
                <BoltIcon />
                {loadingGallery ? "生成中..." : "开始批量渲染"}
              </Button>
            )}

            <div className="mt-3 text-xs text-slate-500">当前风格：{selectedStyleLabel} · Prompt：{resolvedPrompt || "—"}</div>

            {cadDepthUrls && (
              <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
                <div className="text-xs font-semibold text-slate-700">深度图 Checkpoint</div>
                <div className="mt-3 flex gap-3 overflow-auto">
                  {["0", "main", "top", "wall"].filter((k) => cadDepthUrls[k]).map((k) => (
                    <a
                      key={k}
                      href={cadDepthUrls[k]}
                      target="_blank"
                      rel="noreferrer"
                      className="block shrink-0 overflow-hidden rounded-xl border border-slate-200"
                    >
                      <img src={cadDepthUrls[k]} alt={k} className="h-16 w-24 object-cover" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>

          {gallery && (
            <div className="lg:col-span-2">
              <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
                <div className="p-5">
                  <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                    {currentResultUrl && (
                      <img src={currentResultUrl} alt="" className="aspect-[16/9] w-full object-cover" />
                    )}

                    <div className="absolute left-3 top-3 rounded-xl bg-black/55 px-3 py-1 text-xs font-medium text-white">
                      {currentViewLabel}
                    </div>

                    <div className="absolute right-3 top-3 flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-9 w-9 rounded-xl bg-white/80 backdrop-blur hover:bg-white"
                        disabled={!gallery?.length}
                        onClick={() => setResultIndex((v) => Math.max(0, v - 1))}
                        aria-label="上一张"
                      >
                        <span className="text-base leading-none">‹</span>
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-9 w-9 rounded-xl bg-white/80 backdrop-blur hover:bg-white"
                        disabled={!gallery?.length}
                        onClick={() => setResultIndex((v) => Math.min((gallery?.length ?? 1) - 1, v + 1))}
                        aria-label="下一张"
                      >
                        <span className="text-base leading-none">›</span>
                      </Button>
                      <Button
                        variant="default"
                        className="h-9 rounded-xl px-4 shadow-sm"
                        disabled={!currentResultUrl}
                        onClick={downloadCurrentImage}
                      >
                        下载图片
                      </Button>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-3">
                    <div className="text-xs text-slate-500">
                      {gallery.length} 张 · 当前第 {Math.min(resultIndex + 1, gallery.length)} 张
                    </div>
                    <div className="flex items-center gap-2 overflow-auto">
                      {gallery.map((url, idx) => (
                        <button
                          key={`${url}-${idx}`}
                          type="button"
                          onClick={() => setResultIndex(idx)}
                          className={`h-14 w-20 shrink-0 overflow-hidden rounded-xl border transition-colors ${
                            idx === resultIndex ? "border-indigo-300 ring-2 ring-indigo-100" : "border-slate-200 hover:border-slate-300"
                          }`}
                        >
                          <img src={url} alt="" className="h-full w-full object-cover" />
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="border-t border-slate-200 bg-white p-5">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                    <BoltIcon />
                    自然语言精修 (Magic Refinement)
                  </div>
                  <div className="mt-3 flex items-center gap-2">
                    <input
                      value={refineText}
                      onChange={(e) => setRefineText(e.target.value)}
                      placeholder="尝试输入：“把地毯换成浅色木纹”…"
                      className="h-11 flex-1 rounded-xl border border-slate-200 bg-white px-4 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-200"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-11 w-11 rounded-xl"
                      onClick={() => {
                        const v = refineText.trim()
                        if (!v) return
                        showComingSoon("自然语言精修")
                        setRefineText("")
                      }}
                      aria-label="发送"
                    >
                      <span className="text-sm">↗</span>
                    </Button>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {["切换为灰度极简", "增加绿植点缀", "材质更高级更写实"].map((it) => (
                      <button
                        key={it}
                        type="button"
                        className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700 hover:bg-slate-50"
                        onClick={() => setRefineText(it)}
                      >
                        {it}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

