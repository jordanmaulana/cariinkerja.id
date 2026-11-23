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

// Edited CV text, or a fresh PDF that replaces it. The AI re-reads it async.
export async function updateCv(
  input: { cv_text: string } | { resume: File },
): Promise<ProfileMe> {
  const body = new FormData();
  if ("resume" in input) body.append("resume", input.resume);
  else body.append("cv_text", input.cv_text);
  return api<ProfileMe>("/profile/cv/", { method: "POST", body });
}

export async function submitOnboarding(payload: {
  full_name: string;
  phone: string;
  linkedin_url?: string;
  resume?: File;
  bio?: string;
  title: string;
  job_type: JobType[];
  remote_option: RemoteOption[];
}): Promise<ProfileMe> {
  // Multipart so the CV PDF can ride along; lists go as repeated keys.
  const body = new FormData();
  for (const [key, value] of Object.entries(payload)) {
    if (value === undefined || value === "") continue;
    if (Array.isArray(value)) value.forEach((v) => body.append(key, v));
    else body.append(key, value);
  }
  return api<ProfileMe>("/onboarding/", { method: "POST", body });
}
