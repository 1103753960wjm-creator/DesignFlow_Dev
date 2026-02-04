import { Navigate, Route, Routes } from "react-router-dom"

import { RequireAuth } from "@/components/auth/RequireAuth"
import { AppLayout } from "@/components/layout/AppLayout"
import { DashboardPage } from "@/pages/DashboardPage"
import { InteriorPreviewPage } from "@/pages/InteriorPreviewPage"
import { InteriorStudioPage } from "@/pages/InteriorStudioPage"
import { KnowledgePage } from "@/pages/KnowledgePage"
import { LoginPage } from "@/pages/LoginPage"
import { RegisterPage } from "@/pages/RegisterPage"
import { SmartCadUploadPage } from "@/pages/SmartCadUploadPage"
import { WorkshopPage } from "@/pages/WorkshopPage"

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route element={<RequireAuth />}>
        <Route path="/interior-preview" element={<InteriorPreviewPage />} />
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="smart-cad" element={<SmartCadUploadPage />} />
          <Route path="workshop" element={<WorkshopPage />} />
          <Route path="knowledge" element={<KnowledgePage />} />
          <Route path="interior" element={<InteriorStudioPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  )
}
