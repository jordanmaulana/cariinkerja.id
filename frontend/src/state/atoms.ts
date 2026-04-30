import { atom } from "jotai";
import type { AuthUser } from "@/lib/auth";
import { getToken } from "@/lib/auth";

export const selectedJobIdAtom = atom<string | null>(null);

export const tokenAtom = atom<string | null>(
  typeof window === "undefined" ? null : getToken(),
);
export const userAtom = atom<AuthUser | null>(null);
