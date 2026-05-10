import { atom } from "jotai";

import { getToken } from "@/features/auth/api";
import type { AuthUser } from "@/features/auth/types";

export const tokenAtom = atom<string | null>(
  typeof window === "undefined" ? null : getToken(),
);

export const userAtom = atom<AuthUser | null>(null);
