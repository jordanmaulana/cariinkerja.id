import { api } from "@/lib/api";
import type { JobType, RemoteOption } from "@/features/jobs/consts";
import type { AuthResponse, AuthUser, ProfileMe } from "@/features/auth/types";

const TOKEN_KEY = "token";

export function getToken(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function googleSignIn(credential: string): Promise<AuthResponse> {
  const res = await api<AuthResponse>("/auth/google/", {
    method: "POST",
    body: JSON.stringify({ credential }),
    skipAuth: true,
  });
  setToken(res.token);
  return res;
}

export async function logout(): Promise<void> {
  try {
    await api<void>("/auth/logout/", { method: "POST" });
  } finally {
    clearToken();
  }
}

export async function me(): Promise<AuthUser> {
  return api<AuthUser>("/auth/me/");
}

export async function getProfile(): Promise<ProfileMe> {
  return api<ProfileMe>("/profile/me/");
}

export async function submitOnboarding(payload: {
  full_name: string;
  phone: string;
  linkedin_url?: string;
  bio?: string;
  title: string;
  job_type: JobType[];
  remote_option: RemoteOption[];
}): Promise<ProfileMe> {
  return api<ProfileMe>("/onboarding/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
