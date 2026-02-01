export function formatApiError(err: any): string {
  const detail = err?.response?.data?.detail

  if (!detail) return err?.message || "请求失败"

  if (typeof detail === "string") return detail

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        const loc = Array.isArray(item?.loc) ? item.loc.filter((x: any) => x !== "body").join(".") : ""
        const msg = item?.msg ? String(item.msg) : ""
        if (loc && msg) return `${loc}: ${msg}`
        if (msg) return msg
        return null
      })
      .filter(Boolean) as string[]

    return parts.length ? parts.join("\n") : "参数校验失败"
  }

  if (typeof detail === "object") {
    try {
      return JSON.stringify(detail)
    } catch {
      return "请求失败"
    }
  }

  return String(detail)
}

