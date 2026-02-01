import { useEffect, useMemo, useState } from "react"
import { Outlet, useLocation } from "react-router-dom"

import { TopNav } from "@/components/layout/TopNav"
import { clearAccessToken } from "@/lib/auth"
import { getMe } from "@/features/auth/authApi"

export function AppLayout() {
  const location = useLocation()
  const [userLabel, setUserLabel] = useState<string | undefined>(undefined)

  useEffect(() => {
    let cancelled = false
    getMe()
      .then((res) => {
        if (cancelled) return
        const nick = (res.data.nickname || "").trim()
        const email = (res.data.email || "").trim()
        const base = nick || email || "DE"
        const parts = base.split(/[\s@._-]+/).filter(Boolean)
        const two = (parts[0]?.slice(0, 1) || "") + (parts[1]?.slice(0, 1) || parts[0]?.slice(1, 2) || "")
        setUserLabel((two || "DE").toUpperCase())
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  const active = useMemo(() => {
    const p = location.pathname
    if (p.startsWith("/app/knowledge")) return "knowledge" as const
    if (p.startsWith("/app/workshop") || p.startsWith("/app/interior")) return "workshop" as const
    return "home" as const
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-slate-50">
      <TopNav
        active={active}
        userLabel={userLabel}
        onLogout={() => {
          clearAccessToken()
          window.location.href = "/login"
        }}
      />

      <main className="mx-auto min-w-0 max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}

