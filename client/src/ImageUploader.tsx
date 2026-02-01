import { useMemo, useState } from "react"

import { api } from "@/lib/api"

export type UploadResult = {
  file: File
  previewUrl: string
  filename: string
  url: string
  encrypted?: boolean
}

type Props = {
  onUploadSuccess: (result: UploadResult) => void
}

export default function ImageUploader({ onUploadSuccess }: Props) {
  const [preview, setPreview] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isImage = useMemo(() => {
    if (!file) return false
    return /\.(png|jpg|jpeg)$/i.test(file.name)
  }, [file])

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const nextFile = e.target.files?.[0]
    if (!nextFile) return

    setError(null)
    setFile(nextFile)

    const localUrl = URL.createObjectURL(nextFile)
    setPreview(localUrl)

    const formData = new FormData()
    formData.append("file", nextFile)

    setUploading(true)
    try {
      const res = await api.post("/design/upload", formData, { headers: { "Content-Type": "multipart/form-data" } })
      const serverUrl = res.data.url as string
      const filename = res.data.filename as string
      const encrypted = res.data.encrypted as boolean | undefined
      onUploadSuccess({ file: nextFile, previewUrl: localUrl, filename, url: serverUrl, encrypted })
    } catch (err: any) {
      setError(err.response?.data?.detail || "上传失败，请检查后端是否启动")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        {!preview ? (
          <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-200 px-4 py-10 text-center">
            <div className="text-2xl font-semibold text-slate-900">+</div>
            <div className="text-sm text-slate-600">点击上传 CAD（.dxf/.dwg）或参考图（.jpg/.png）</div>
            <input type="file" className="hidden" accept=".jpg,.png,.jpeg,.dxf,.dwg" onChange={handleFileChange} />
          </label>
        ) : (
          <div className="space-y-3">
            {isImage ? (
              <img src={preview} alt="Preview" className="h-64 w-full rounded-xl object-cover" />
            ) : (
              <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="text-sm font-medium text-slate-900">{file?.name}</div>
                <div className="text-xs text-slate-500">CAD 文件</div>
              </div>
            )}

            {uploading && <div className="text-sm text-slate-600">正在上传服务器...</div>}
            {error && <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
          </div>
        )}
      </div>
    </div>
  )
}
