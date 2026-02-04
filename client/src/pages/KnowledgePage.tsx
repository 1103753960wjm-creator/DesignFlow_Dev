import { useEffect, useMemo, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type Domain = "interior" | "landscape" | "poster"
type MaterialStatus = "learning" | "active"

type MaterialItem = {
  id: string
  domain: Domain
  name: string
  sizeBytes: number
  status: MaterialStatus
  uploadedAt: number
}

const STORAGE_KEY = "knowledgeMaterials:v1"
const LEARNING_MS = 10_000

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0B"
  const units = ["B", "KB", "MB", "GB", "TB"] as const
  let v = bytes
  let idx = 0
  while (v >= 1024 && idx < units.length - 1) {
    v /= 1024
    idx += 1
  }
  const n = idx === 0 ? Math.round(v) : Math.round(v * 10) / 10
  return `${n}${units[idx]}`
}

function getDomainLabel(domain: Domain) {
  if (domain === "interior") return "室内设计"
  if (domain === "landscape") return "景观设计"
  return "海报设计"
}

function getStatusLabel(status: MaterialStatus) {
  return status === "learning" ? "学习中" : "生效中"
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0 4 4m-4-4-4 4" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
    </svg>
  )
}

function FileIcon({ name }: { name: string }) {
  const ext = name.toLowerCase().split(".").pop() || ""
  const kind = (() => {
    if (["pdf"].includes(ext)) return "pdf" as const
    if (["xls", "xlsx", "csv"].includes(ext)) return "sheet" as const
    if (["zip", "rar", "7z"].includes(ext)) return "archive" as const
    if (["png", "jpg", "jpeg", "webp", "gif"].includes(ext)) return "image" as const
    return "file" as const
  })()

  const tone =
    kind === "pdf"
      ? "bg-orange-50 text-orange-600"
      : kind === "sheet"
        ? "bg-emerald-50 text-emerald-600"
        : kind === "archive"
          ? "bg-violet-50 text-violet-600"
          : kind === "image"
            ? "bg-sky-50 text-sky-600"
            : "bg-slate-50 text-slate-600"

  return (
    <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200", tone)}>
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7 3h7l3 3v15a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M14 3v4a1 1 0 0 0 1 1h4" />
      </svg>
    </div>
  )
}

function StatusBadge({ status }: { status: MaterialStatus }) {
  if (status === "active") {
    return (
      <div className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="m5 13 4 4L19 7" />
        </svg>
        生效中
      </div>
    )
  }
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800">
      <span className="relative inline-flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-500" />
      </span>
      学习中
    </div>
  )
}

function safeParseMaterials(raw: string | null): MaterialItem[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    const isRecord = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object"
    const items: MaterialItem[] = []
    for (const it of parsed) {
      if (!isRecord(it)) continue
      const domain = it.domain
      const status = it.status
      const id = it.id
      const name = it.name
      const sizeBytes = it.sizeBytes
      const uploadedAt = it.uploadedAt
      if (domain !== "interior" && domain !== "landscape" && domain !== "poster") continue
      if (status !== "learning" && status !== "active") continue
      if (typeof id !== "string" || typeof name !== "string") continue
      if (typeof sizeBytes !== "number" || typeof uploadedAt !== "number") continue
      if (!["interior", "landscape", "poster"].includes(domain)) continue
      if (!["learning", "active"].includes(status)) continue
      items.push({
        id,
        domain,
        name,
        sizeBytes,
        status,
        uploadedAt,
      })
    }
    return items
  } catch {
    return []
  }
}

export function KnowledgePage() {
  const [domain, setDomain] = useState<Domain>("interior")
  const [materials, setMaterials] = useState<MaterialItem[]>(() => safeParseMaterials(localStorage.getItem(STORAGE_KEY)))
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const makeId = () => (globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(materials))
  }, [materials])

  useEffect(() => {
    if (materials.every((m) => m.status !== "learning")) return
    const id = window.setInterval(() => {
      const now = Date.now()
      setMaterials((prev) =>
        prev.map((m) => {
          if (m.status !== "learning") return m
          return now - m.uploadedAt >= LEARNING_MS ? { ...m, status: "active" } : m
        })
      )
    }, 800)
    return () => window.clearInterval(id)
  }, [materials])

  const visible = useMemo(() => materials.filter((m) => m.domain === domain).sort((a, b) => b.uploadedAt - a.uploadedAt), [domain, materials])

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="text-2xl font-semibold text-slate-900">专业知识库</div>
          <div className="text-sm text-slate-600">分类域管理您的设计资产，训练专属 AI 助手。</div>
        </div>

        <div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              const files = Array.from(e.target.files ?? [])
              if (!files.length) return
              const now = Date.now()
              setMaterials((prev) => [
                ...files.map((f) => ({
                  id: makeId(),
                  domain,
                  name: f.name,
                  sizeBytes: f.size,
                  status: "learning" as const,
                  uploadedAt: now,
                })),
                ...prev,
              ])
              e.currentTarget.value = ""
            }}
          />
          <Button onClick={() => fileInputRef.current?.click()} className="gap-2 rounded-xl">
            <UploadIcon className="h-4 w-4" />
            上传新资料
          </Button>
        </div>
      </div>

      <div className="mt-6 flex items-center gap-2 rounded-xl bg-slate-50 p-1 text-sm">
        {([
          { key: "interior", label: "室内设计" },
          { key: "landscape", label: "景观设计" },
          { key: "poster", label: "海报设计" },
        ] as const).map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setDomain(t.key)}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-4 py-2 font-medium text-slate-600 transition-colors",
              domain === t.key && "bg-white text-indigo-600 shadow-sm"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-8">
        <div className="flex items-center gap-3">
          <div className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-600">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h10M7 12h10M7 17h6" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 21h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H9L7 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2Z" />
            </svg>
          </div>
          <div className="text-base font-semibold text-slate-900">{getDomainLabel(domain)} · 资料列表</div>
        </div>

        <div className="mt-4 space-y-3">
          {visible.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-10 text-center text-sm text-slate-600">
              暂无资料，点击右上角“上传新资料”开始训练专属知识库。
            </div>
          ) : (
            visible.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm"
              >
                <div className="flex min-w-0 items-center gap-4">
                  <FileIcon name={m.name} />
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-slate-900">{m.name}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {formatBytes(m.sizeBytes)} · 状态：{getStatusLabel(m.status)}
                    </div>
                  </div>
                </div>
                <StatusBadge status={m.status} />
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

