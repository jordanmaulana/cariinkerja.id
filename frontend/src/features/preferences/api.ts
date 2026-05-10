import { api } from "@/lib/api";
import type {
  Preference,
  PreferencePayload,
} from "@/features/preferences/types";

export async function listPreferences(): Promise<Preference[]> {
  return api<Preference[]>("/preferences/");
}

export async function getPreference(id: string): Promise<Preference> {
  return api<Preference>(`/preferences/${id}/`);
}

export async function createPreference(
  payload: PreferencePayload,
): Promise<Preference> {
  return api<Preference>("/preferences/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updatePreference(
  id: string,
  payload: PreferencePayload,
): Promise<Preference> {
  return api<Preference>(`/preferences/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deletePreference(id: string): Promise<void> {
  await api<void>(`/preferences/${id}/`, { method: "DELETE" });
}
