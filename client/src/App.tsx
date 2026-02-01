import { Navigate, Route, Routes } from "react-router-dom"

import { RequireAuth } from "@/components/auth/RequireAuth"
import { AppLayout } from "@/components/layout/AppLayout"
import { DashboardPage } from "@/pages/DashboardPage"
import { InteriorPreviewPage } from "@/pages/InteriorPreviewPage"
import { InteriorStudioPage } from "@/pages/InteriorStudioPage"
import { KnowledgePage } from "@/pages/KnowledgePage"
import { LandingPage } from "@/pages/LandingPage"
import { LoginPage } from "@/pages/LoginPage"
import { RegisterPage } from "@/pages/RegisterPage"
import { WorkshopPage } from "@/pages/WorkshopPage"

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<RequireAuth />}>
        <Route path="/interior-preview" element={<InteriorPreviewPage />} />
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="workshop" element={<WorkshopPage />} />
          <Route path="knowledge" element={<KnowledgePage />} />
          <Route path="interior" element={<InteriorStudioPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
