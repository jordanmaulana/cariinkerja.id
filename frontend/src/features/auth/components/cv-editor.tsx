import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Lock, Upload } from "lucide-react";
import { toast } from "react-toastify";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { updateCv } from "@/features/auth/api";
import type { ProfileMe } from "@/features/auth/types";
import { formatDateTime } from "@/lib/utils";

// Mirror profiles/services.py RESUME_MIN_CHARS / RESUME_MAX_BYTES.
const MIN_CHARS = 200;
const MAX_PDF_BYTES = 5 * 1024 * 1024;
const CONFIRM_ONCE_A_DAY =
  "CV cuma bisa diubah 1x sehari. Abis ini kamu baru bisa ubah lagi besok. Lanjut?";

export function CvEditor({ profile }: { profile: ProfileMe }) {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const saved = profile.cv_text ?? "";
  const [text, setText] = useState(saved);
  const [error, setError] = useState<string | null>(null);
  // linkedin_ingested_at at save time; the AI is done once it moves on.
  const [pendingFrom, setPendingFrom] = useState<{ at: string | null } | null>(
    null,
  );
  const pending =
    pendingFrom !== null && profile.linkedin_ingested_at === pendingFrom.at;
  // Server sends null once the day is up; a window refocus refetches it.
  const lockedUntil = profile.cv_next_edit_at;

  const mutation = useMutation({
    mutationFn: updateCv,
    onSuccess: (updated) => {
      queryClient.setQueryData(["profile", "me"], updated);
      setText(updated.cv_text ?? "");
      if ((updated.cv_text ?? "").trim() !== saved.trim()) {
        setPendingFrom({ at: profile.linkedin_ingested_at });
        toast.success("CV tersimpan. AI lagi baca ulang profilmu.");
      } else {
        toast.info("Nggak ada yang berubah.");
      }
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Gagal menyimpan CV.");
      // A 429 means the daily gate closed elsewhere (e.g. another tab): show the lock.
      queryClient.invalidateQueries({ queryKey: ["profile", "me"] });
    },
  });

  const trimmed = text.trim();
  const dirty = trimmed !== saved.trim();
  const tooShort = trimmed.length < MIN_CHARS;

  function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!window.confirm(CONFIRM_ONCE_A_DAY)) return;
    setError(null);
    mutation.mutate({ cv_text: text });
  }

  function onPickPdf(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (file.size > MAX_PDF_BYTES) {
      setError("CV maksimal 5 MB.");
      return;
    }
    const replaceNote = dirty
      ? "Perubahan yang belum disimpan bakal diganti isi PDF baru. "
      : "";
    if (!window.confirm(replaceNote + CONFIRM_ONCE_A_DAY)) return;
    setError(null);
    mutation.mutate({ resume: file });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Teks CV</CardTitle>
        <CardDescription>
          Ini teks yang kami ambil dari CV-mu, dan ini yang dibaca AI. Rapikan
          kalau ada yang berantakan atau kurang: pengalaman, skill, ringkasan.
          Penilaian loker berikutnya pakai versi terbaru.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSave} className="space-y-3">
          {lockedUntil ? (
            <p className="flex items-start gap-2 rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground">
              <Lock className="mt-0.5 size-4 shrink-0" />
              Kamu udah ubah CV dalam 24 jam terakhir. Bisa diubah lagi mulai{" "}
              {formatDateTime(lockedUntil)}.
            </p>
          ) : (
            <p className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              CV cuma bisa diubah 1x sehari (termasuk upload ulang PDF). Rapikan
              semuanya dulu, baru simpan.
            </p>
          )}
          <textarea
            aria-label="Teks CV"
            rows={20}
            value={text}
            readOnly={!!lockedUntil}
            onChange={(e) => setText(e.target.value)}
            aria-invalid={dirty && tooShort}
            className="w-full rounded border bg-background px-3 py-2 text-sm leading-relaxed"
          />
          <p
            className={
              dirty && tooShort
                ? "text-xs text-red-600"
                : "text-xs text-muted-foreground"
            }
          >
            {trimmed.length.toLocaleString("id-ID")} karakter
            {tooShort && ` (minimal ${MIN_CHARS})`}
          </p>
          {pending && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              AI lagi baca ulang CV-mu. Status di atas ke-update sendiri.
            </p>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex flex-wrap gap-2">
            <Button
              type="submit"
              disabled={!dirty || tooShort || !!lockedUntil || mutation.isPending}
            >
              {mutation.isPending ? "Menyimpan…" : "Simpan"}
            </Button>
            {dirty && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => setText(saved)}
                disabled={mutation.isPending}
              >
                Batal
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              onClick={() => fileRef.current?.click()}
              disabled={!!lockedUntil || mutation.isPending}
            >
              <Upload className="size-4" />
              Upload ulang PDF
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf,.pdf"
              onChange={onPickPdf}
              className="hidden"
            />
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
