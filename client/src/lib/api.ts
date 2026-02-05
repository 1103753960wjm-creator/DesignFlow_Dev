import axios from "axios"

import { getAccessToken } from "@/lib/auth"

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8002/api/v1",
  timeout: 60_000,
})

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export type EngineeringUploadResponse = {
  status: "success"
  dxf_file_path: string
  svg_preview: string
}

export type EngineeringUploadImageResponse = {
  status: "converted"
  dxf_file_path: string
  dxf_url: string
  svg_preview: string
  session_id: string
}

export type EngineeringModifyResponse = {
  status: "success"
  svg_preview: string
}

export async function uploadCadFile(file: File): Promise<EngineeringUploadResponse> {
  const formData = new FormData()
  formData.append("file", file)
  const resp = await api.post<EngineeringUploadResponse>("/engineering/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return resp.data
}

export async function uploadCadImage(file: File): Promise<EngineeringUploadImageResponse> {
  const formData = new FormData()
  formData.append("file", file)
  const resp = await api.post<EngineeringUploadImageResponse>("/engineering/upload/image", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return resp.data
}

export async function modifyCadStructure(dxfPath: string, command: string): Promise<EngineeringModifyResponse> {
  const resp = await api.post<EngineeringModifyResponse>("/engineering/modify", {
    dxf_file_path: dxfPath,
    user_prompt: command,
  })
  return resp.data
}

