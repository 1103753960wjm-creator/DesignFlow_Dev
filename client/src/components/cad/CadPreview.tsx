import { useEffect, useMemo, useRef, useState } from "react"

import DxfParser from "dxf-parser"
import { Viewer } from "three-dxf"

import { Button } from "@/components/ui/button"

type Props = {
  file: File
  className?: string
}

export function CadPreview({ file, className }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<any>(null)
  const [error, setError] = useState<string | null>(null)

  const isDxf = useMemo(() => file.name.toLowerCase().endsWith(".dxf"), [file.name])

  useEffect(() => {
    let cancelled = false

    async function run() {
      setError(null)
      viewerRef.current = null

      const container = containerRef.current
      if (!container) return

      container.innerHTML = ""

      if (!isDxf) {
        setError("仅支持 .dxf 预览")
        return
      }

      try {
        const text = await file.text()
        if (cancelled) return

        const parser = new DxfParser()
        const dxf = parser.parseSync(text)

        const width = Math.max(1, container.clientWidth)
        const height = Math.max(1, container.clientHeight)
        viewerRef.current = new (Viewer as any)(dxf, container, width, height)

        const onResize = () => {
          const nextW = Math.max(1, container.clientWidth)
          const nextH = Math.max(1, container.clientHeight)
          viewerRef.current?.resize?.(nextW, nextH)
        }
        window.addEventListener("resize", onResize)

        return () => window.removeEventListener("resize", onResize)
      } catch (e: any) {
        setError(e?.message || "DXF 解析失败")
      }
    }

    let cleanupResize: void | (() => void)
    run().then((cleanup) => {
      cleanupResize = cleanup as any
    })

    return () => {
      cancelled = true
      cleanupResize?.()
      const container = containerRef.current
      if (container) container.innerHTML = ""
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

