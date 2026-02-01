import { api } from "@/lib/api"

export type LoginRequest = {
  email: string
  password: string
}

export type RegisterRequest = {
  email: string
  phone: string
  password: string
  nickname?: string
}

export type TokenResponse = {
  access_token: string
  token_type: "bearer"
}

export async function register(payload: RegisterRequest) {
  return api.post<TokenResponse>("/auth/register", payload)
}

export async function login(payload: LoginRequest) {
  return api.post<TokenResponse>("/auth/login", payload)
}

export async function getMe() {
  return api.get<{ id: string; email: string; nickname: string | null }>("/auth/me")
}

