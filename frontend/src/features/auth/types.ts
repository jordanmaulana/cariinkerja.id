export type AuthUser = {
  id: number;
  email: string;
  full_name: string | null;
  onboarded: boolean;
};

export type AuthResponse = { token: string; user: AuthUser };

export type ProfileMe = {
  full_name: string | null;
  suggested_full_name: string;
  phone: string | null;
  linkedin_url: string | null;
  bio: string | null;
  onboarded: boolean;
  linkedin_quality_ok: boolean;
  linkedin_quality_reason: string;
  linkedin_ingested_at: string | null;
  // Set only for CV profiles (no LinkedIn URL).
  cv_text: string | null;
  // Set while the 1-change-per-day CV gate is closed.
  cv_next_edit_at: string | null;
};
