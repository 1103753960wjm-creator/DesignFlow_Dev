import { useEffect, useMemo, useRef, useState } from "react"

import DxfParser from "dxf-parser"
import { Viewer } from "three-dxf"

import { Button } from "@/components/ui/button"

type Props = {
  file: File
  className?: string
}

type ViewerInstance = {
  resize?: (width: number, height: number) => void
  render?: () => void
  renderer?: { dispose?: () => void }
}

export function CadPreview({ file, className }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<ViewerInstance | null>(null)
  const [error, setError] = useState<string | null>(null)

  const isDxf = useMemo(() => file.name.toLowerCase().endsWith(".dxf"), [file.name])

  useEffect(() => {
    let cancelled = false
    const containerEl = containerRef.current

    async function run(): Promise<void | (() => void)> {
      setError(null)
      viewerRef.current = null

      if (!containerEl) return

      containerEl.innerHTML = ""

      if (!isDxf) {
        setError("仅支持 .dxf 预览")
        return
      }

      try {
        const text = await file.text()
        if (cancelled) return

        const parser = new DxfParser()
        const dxf = parser.parseSync(text)

        const width = Math.max(1, containerEl.clientWidth)
        const height = Math.max(1, containerEl.clientHeight)
        const ViewerCtor = Viewer as unknown as new (dxf: unknown, el: HTMLElement, w: number, h: number) => ViewerInstance
        viewerRef.current = new ViewerCtor(dxf as unknown, containerEl, width, height)

        const onResize = () => {
          const nextW = Math.max(1, containerEl.clientWidth)
          const nextH = Math.max(1, containerEl.clientHeight)
          viewerRef.current?.resize?.(nextW, nextH)
        }
        window.addEventListener("resize", onResize)

        return () => window.removeEventListener("resize", onResize)
      } catch (e: unknown) {
        const msg = e && typeof e === "object" && "message" in e ? (e as { message?: unknown }).message : undefined
        setError(typeof msg === "string" && msg.trim() ? msg : "DXF 解析失败")
      }
    }

    let cleanupResize: void | (() => void)
    run().then((cleanup) => {
      cleanupResize = cleanup
    })

    return () => {
      cancelled = true
      cleanupResize?.()
      if (containerEl) containerEl.innerHTML = ""
      const renderer = viewerRef.current?.renderer
      renderer?.dispose?.()
      viewerRef.current = null
    }
  }, [file, isDxf])

  return (
    <div className={className}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-medium text-slate-900">CAD 轻预览</div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
          const container = containerRef.current
          if (!container) return
          viewerRef.current?.resize?.(Math.max(1, container.clientWidth), Math.max(1, container.clientHeight))
            viewerRef.current?.render?.()
          }}
        >
          刷新视图
        </Button>
      </div>
      {error && <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      <div
        ref={containerRef}
        className="mt-3 h-[420px] w-full overflow-hidden rounded-xl border border-slate-200 bg-white"
      />
    </div>
  )
}

