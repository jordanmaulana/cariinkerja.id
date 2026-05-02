export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, message: string, data: unknown) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export type ApiInit = RequestInit & { skipAuth?: boolean };

const API_BASE = `${import.meta.env.VITE_API_URL ?? ""}/api/v1`;

export async function api<T>(path: string, init?: ApiInit): Promise<T> {
  const { skipAuth, ...rest } = init ?? {};
  const token =
    !skipAuth && typeof window !== "undefined"
      ? localStorage.getItem("token")
      : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((rest.headers as Record<string, string>) ?? {}),
  };
  if (token) headers["Authorization"] = `Token ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...rest, headers });
  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const message =
      (data && (data.detail || JSON.stringify(data))) ||
      `${res.status} ${res.statusText}`;
    throw new ApiError(res.status, message, data);
  }
  return data as T;
}
