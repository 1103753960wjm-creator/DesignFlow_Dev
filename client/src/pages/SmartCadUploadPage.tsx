import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V7" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.5 10.5 12 7l3.5 3.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 17.5A3.5 3.5 0 0 0 7.5 21h9A3.5 3.5 0 0 0 20 17.5" />
    </svg>
  )
}

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
  const [dragActive, setDragActive] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  function handlePickFile(file?: File | null) {
    if (!file) return
    setSelectedFile(file)
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
            <div className="text-xs text-slate-500">上传平面位图/手绘稿，自动结构化并生成可渲染的 3D 白模</div>
          </div>
        </div>

        <div className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
          施工图标准 v2.0
        </div>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div
          className={`m-4 flex min-h-[560px] cursor-pointer items-center justify-center rounded-3xl bg-gradient-to-br from-[#0b1220] via-[#0b1a3b] to-[#07101f] ${
            dragActive ? "ring-2 ring-indigo-400/60 ring-offset-2 ring-offset-white" : ""
          }`}
          onClick={() => fileInputRef.current?.click()}
          onDragEnter={(e) => {
            e.preventDefault()
            e.stopPropagation()
            setDragActive(true)
          }}
          onDragOver={(e) => {
            e.preventDefault()
            e.stopPropagation()
            setDragActive(true)
          }}
          onDragLeave={(e) => {
            e.preventDefault()
            e.stopPropagation()
            if (e.currentTarget === e.target) setDragActive(false)
          }}
          onDrop={(e) => {
            e.preventDefault()
            e.stopPropagation()
            setDragActive(false)
            handlePickFile(e.dataTransfer.files?.[0])
          }}
        >
          <div className="max-w-md text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-white/10 text-white">
              <UploadIcon />
            </div>
            <div className="mt-6 text-2xl font-semibold text-white">上传平面位图 / 手绘稿</div>
            <div className="mt-2 text-sm text-white/70">支持 JPG/PNG → 自动转 DXF 矢量图</div>
            <div className="mt-1 text-xs text-white/45">也支持直接上传 DXF（施工图）</div>

            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".jpg,.png,.jpeg,.dxf,.dwg"
              onChange={(e) => handlePickFile(e.target.files?.[0])}
            />

            <Button
              variant="outline"
              className="mt-7 h-11 rounded-xl border-white/20 bg-white/10 px-8 text-white hover:bg-white/15 hover:text-white"
              onClick={(e) => {
                e.stopPropagation()
                fileInputRef.current?.click()
              }}
            >
              选择文件
            </Button>

            {selectedFile && (
              <div className="mt-4 text-xs text-white/60">
                已选择：<span className="font-medium text-white/85">{selectedFile.name}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
