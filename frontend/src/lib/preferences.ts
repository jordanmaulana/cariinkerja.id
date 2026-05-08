import { api } from "@/lib/api"
import type { JobType, RemoteOption } from "@/lib/consts"

export type PreferenceStatus =
  | "waiting_payment"
  | "waiting_admin"
  | "running"
  | "expired"

export type PreferenceSource = "jobstreet" | "indeed"

export type Preference = {
  id: string
  title: string | null
  job_type: JobType[]
  remote_option: RemoteOption[]
  crawl_url: string | null
  crawl_source: PreferenceSource | null
  status: PreferenceStatus
  created_on: string
  updated_on: string
}

export const PREFERENCE_STATUSES: { value: PreferenceStatus; label: string }[] = [
  { value: "waiting_payment", label: "Menunggu pembayaran" },
  { value: "waiting_admin", label: "Lagi ngumpulin loker yang kamu cari" },
  { value: "running", label: "Berjalan" },
  { value: "expired", label: "Kedaluwarsa" },
]

export type PreferencePayload = {
  title?: string | null
  job_type?: JobType[]
  remote_option?: RemoteOption[]
}

export async function listPreferences(): Promise<Preference[]> {
  return api<Preference[]>("/preferences/")
}

export async function getPreference(id: string): Promise<Preference> {
  return api<Preference>(`/preferences/${id}/`)
}

export async function createPreference(
  payload: PreferencePayload,
): Promise<Preference> {
  return api<Preference>("/preferences/", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function updatePreference(
  id: string,
  payload: PreferencePayload,
): Promise<Preference> {
  return api<Preference>(`/preferences/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export async function deletePreference(id: string): Promise<void> {
  await api<void>(`/preferences/${id}/`, { method: "DELETE" })
}
