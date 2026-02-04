const isRecord = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object"

export function formatApiError(err: unknown): string {
  const message = (() => {
    if (isRecord(err) && typeof err.message === "string" && err.message.trim()) return err.message
    return "请求失败"
  })()

  const detail = (() => {
    if (!isRecord(err)) return undefined
    const response = err.response
    if (!isRecord(response)) return undefined
    const data = response.data
    if (!isRecord(data)) return undefined
    return data.detail
  })()

  if (!detail) return message

  if (typeof detail === "string") return detail

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (!isRecord(item)) return null
        const loc = (() => {
          const raw = item.loc
          if (!Array.isArray(raw)) return ""
          const segs = raw
            .filter((x) => x !== "body")
            .map((x) => (typeof x === "string" || typeof x === "number" ? String(x) : ""))
            .filter(Boolean)
          return segs.join(".")
        })()
        const msg = typeof item.msg === "string" ? item.msg : item.msg != null ? String(item.msg) : ""
        if (loc && msg) return `${loc}: ${msg}`
        if (msg) return msg
        return null
      })
      .filter((x): x is string => !!x)

    return parts.length ? parts.join("\n") : "参数校验失败"
  }

  if (typeof detail === "object") {
    try {
      return JSON.stringify(detail)
    } catch {
      return message
    }
  }

  return String(detail)
}

