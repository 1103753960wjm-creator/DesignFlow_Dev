import { useMemo, useRef, useState } from "react"

import axios from "axios"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { modifyCadStructure, uploadCadImage } from "@/lib/api"

type UploadedCad = {
  name: string
  dxfPath: string
  downloadUrl: string
  svg: string
  debugImages: string[]
}

type ToastState = { message: string } | null

function CadEngineIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 3h10a2 2 0 0 1 2 2v4l-4 4v8H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9h-4V5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.5 14.5h4" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.5 17.5h4" />
    </svg>
  )
}

export function SmartCadUploadPage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [toast, setToast] = useState<ToastState>(null)
  const [files, setFiles] = useState<UploadedCad[]>([])
  const [activeIndex, setActiveIndex] = useState(0)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [dxfDownloadUrl, setDxfDownloadUrl] = useState<string | null>(null)
  const [prompt, setPrompt] = useState("")
  const [modifying, setModifying] = useState(false)

  const active = useMemo(() => files[activeIndex] ?? null, [files, activeIndex])
  const resolvedDownloadUrl = useMemo(() => {
    if (!dxfDownloadUrl) return null
    const raw = dxfDownloadUrl.trim()
    if (!raw) return null
    if (raw.startsWith("http://") || raw.startsWith("https://")) return raw
    const base = import.meta.env.VITE_API_BASE_URL ?? window.location.origin
    let origin = window.location.origin
    try {
      origin = new URL(base).origin
    } catch {
      origin = window.location.origin
    }
    if (raw.startsWith("/")) return `${origin}${raw}`
    return `${origin}/${raw}`
  }, [dxfDownloadUrl])

  const resolvedDebugImages = useMemo(() => {
    const list = active?.debugImages ?? []
    const base = import.meta.env.VITE_API_BASE_URL ?? window.location.origin
    let origin = window.location.origin
    try {
      origin = new URL(base).origin
    } catch {
      origin = window.location.origin
    }
    return list
      .map((u) => String(u ?? "").trim())
      .filter(Boolean)
      .map((u) => {
        if (u.startsWith("http://") || u.startsWith("https://")) return u
        if (u.startsWith("/")) return `${origin}${u}`
        return `${origin}/${u}`
      })
  }, [active?.debugImages])

  function showToast(message: string) {
    setToast({ message })
    window.setTimeout(() => setToast(null), 2600)
  }

  async function handleUpload(file: File) {
    setUploading(true)
    try {
      const data = await uploadCadImage(file)
      const next: UploadedCad = {
        name: file.name,
        dxfPath: data.dxf_file_path,
        downloadUrl: data.dxf_url,
        svg: data.svg_preview,
        debugImages: data.debug_images ?? [],
      }
      setFiles((prev) => {
        const list = [next, ...prev]
        setActiveIndex(0)
        return list
      })
      setDxfDownloadUrl(data.dxf_url)
      setSelectedFile(null)
      showToast("矢量化完成，已生成 CAD 预览")
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 422) {
        showToast("图片清晰度不足")
        return
      }
      if (axios.isAxiosError(e)) {
        showToast(e.response?.data?.detail ?? "矢量化失败")
      } else {
        showToast("矢量化失败")
      }
    } finally {
      setUploading(false)
    }
  }

  async function handleModify() {
    if (!active) {
      showToast("请先上传户型图并完成矢量化")
      return
    }
    const cmd = prompt.trim()
    if (!cmd) {
      showToast("请输入修改指令")
      return
    }
    setModifying(true)
    try {
      const data = await modifyCadStructure(active.dxfPath, cmd)
      setFiles((prev) => {
        const next = [...prev]
        const cur = next[activeIndex]
        if (cur) next[activeIndex] = { ...cur, svg: data.svg_preview }
        return next
      })
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 400) {
        showToast("指令不清晰，请重试")
        return
      }
      if (axios.isAxiosError(e)) {
        showToast(e.response?.data?.detail ?? "修改失败")
      } else {
        showToast("修改失败")
      }
    } finally {
      setModifying(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-700">
            <CadEngineIcon />
          </div>
          <div className="min-w-0">
            <div className="truncate text-lg font-semibold text-slate-900">
              智能 CAD 引擎 <span className="font-normal text-slate-500">(Smart CAD Engine)</span>
            </div>
            <div className="text-xs text-slate-500">上传户型图 → AI 矢量化为 CAD → 预览 SVG → 自然语言修改</div>
          </div>
        </div>
        <div className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
          V1.6 极速预览链路
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        <Card className="p-4">
          <div className="text-sm font-semibold text-slate-900">户型图上传</div>
          <div className="mt-3 space-y-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,image/*"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) setSelectedFile(f)
              }}
            />
            <Button
              className="w-full"
              disabled={uploading}
              onClick={() => {
                if (!selectedFile) {
                  fileInputRef.current?.click()
                  return
                }
                void handleUpload(selectedFile)
              }}
            >
              {selectedFile ? (uploading ? "正在 AI 矢量化..." : `开始矢量化 ${selectedFile.name}`) : "选择 JPG/PNG"}
            </Button>
            {selectedFile && (
              <Button
                variant="outline"
                className="w-full"
                disabled={uploading}
                onClick={() => {
                  setSelectedFile(null)
                  if (fileInputRef.current) fileInputRef.current.value = ""
                }}
              >
                清除选择
              </Button>
            )}
          </div>

          <div className="mt-5 text-xs text-slate-500">已上传</div>
          <div className="mt-2 space-y-2">
            {files.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 p-3 text-xs text-slate-500">
                还没有文件。先上传一张户型图开始矢量化与修改。
              </div>
            ) : (
              files.map((f, idx) => (
                <button
                  key={`${f.dxfPath}-${idx}`}
                  className={`w-full rounded-xl border px-3 py-2 text-left text-xs transition-colors ${
                    idx === activeIndex
                      ? "border-indigo-200 bg-indigo-50 text-indigo-900"
                      : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  }`}
                  onClick={() => {
                    setActiveIndex(idx)
                    setDxfDownloadUrl(f.downloadUrl)
                  }}
                  type="button"
                >
                  <div className="truncate font-medium">{f.name}</div>
                  <div className="mt-1 truncate text-[11px] text-slate-500">{f.dxfPath}</div>
                </button>
              ))
            )}
          </div>
        </Card>

        <Card className="flex min-h-[640px] flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div className="text-sm font-semibold text-slate-900">SVG 预览</div>
            <div className="flex items-center gap-2">
              {resolvedDownloadUrl && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(resolvedDownloadUrl, "_blank", "noreferrer")}
                >
                  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v10" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 11l4 4 4-4" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 19h16" />
                  </svg>
                  下载 CAD 源文件 (.dxf)
                </Button>
              )}
              <div className="text-xs text-slate-500">{active ? active.name : "未选择"}</div>
            </div>
          </div>

          <div className="relative flex-1 bg-slate-50">
            {modifying && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/60 text-sm font-medium text-slate-700">
                正在修改...
              </div>
            )}
            <div className="h-full w-full p-4 [&_svg]:h-full [&_svg]:w-full">
              {active?.svg ? (
                <div className="h-full w-full rounded-2xl border border-slate-200 bg-white p-3">
                  <div className="h-full w-full" dangerouslySetInnerHTML={{ __html: active.svg }} />
                </div>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-slate-500">
                  上传户型图并完成矢量化后将显示预览 SVG
                </div>
              )}
            </div>
          </div>

          {resolvedDebugImages.length > 0 && (
            <details className="border-t border-slate-200 px-4 py-3">
              <summary className="cursor-pointer select-none text-sm font-semibold text-slate-900">
                🛠️ 算法调试视图
              </summary>
              <div className="mt-3 flex gap-3 overflow-x-auto pb-2">
                {resolvedDebugImages.map((url) => (
                  <div key={url} className="w-[260px] shrink-0 overflow-hidden rounded-xl border border-slate-200 bg-white">
                    <img src={url} className="h-44 w-full object-contain bg-slate-50" alt="debug" loading="lazy" />
                    <div className="border-t border-slate-200 px-3 py-2 text-[11px] text-slate-600">{url.split("/").pop()}</div>
                  </div>
                ))}
              </div>
            </details>
          )}

          <div className="border-t border-slate-200 p-4">
            <div className="flex gap-2">
              <Input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder='例如："Remove the north wall" 或 "把客厅的墙向右移动 500mm"'
                disabled={!active || uploading || modifying}
              />
              <Button onClick={() => void handleModify()} disabled={!active || uploading || modifying}>
                {modifying ? "处理中..." : "Magic Modify"}
              </Button>
            </div>
            <div className="mt-2 text-xs text-slate-500">
              若后端返回 400，将提示“指令不清晰，请重试”。请确保后端已配置 LLM_PROVIDER 与 API Key。
            </div>
          </div>
        </Card>
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 shadow-lg">
          {toast.message}
        </div>
      )}
    </div>
  )
}
