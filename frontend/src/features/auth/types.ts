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
};
