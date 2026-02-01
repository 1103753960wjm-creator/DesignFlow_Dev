import { Navigate, Outlet, useLocation } from "react-router-dom"

import { getAccessToken } from "@/lib/auth"

export function RequireAuth() {
  const location = useLocation()
  const token = getAccessToken()
  if (!token) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  return <Outlet />
}

