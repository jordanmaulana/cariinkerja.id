import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-toastify";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  buildInitialValues,
  PreferenceFormFields,
  type PreferenceFormValues,
  valuesToPayload,
} from "@/features/preferences/components/preference-form";
import { DeleteDialog } from "@/features/preferences/components/delete-dialog";
import { deletePreference, updatePreference } from "@/features/preferences/api";
import type { Preference } from "@/features/preferences/types";
import { arraysEqual } from "@/features/preferences/utils";

export function PreferenceEditor({ preference }: { preference: Preference }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [values, setValues] = useState<PreferenceFormValues>(() =>
    buildInitialValues(preference),
  );
  const [error, setError] = useState<string | null>(null);
  const isRunning = preference.status === "running";
  const canDelete = preference.status === "waiting_payment";

  const updateMutation = useMutation({
    mutationFn: (v: PreferenceFormValues) =>
      updatePreference(preference.id, valuesToPayload(v)),
    onSuccess: (updated) => {
      const wasRunning = isRunning;
      queryClient.setQueryData(["preference", preference.id], updated);
      queryClient.invalidateQueries({ queryKey: ["preferences"] });
      setValues(buildInitialValues(updated));
      if (wasRunning) {
        toast.warning(
          "Tersimpan. Crawl dijeda — dikirim ulang ke admin untuk ditinjau sebelum berjalan lagi.",
        );
      } else {
        toast.success("Pencarian diperbarui.");
      }
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Gagal menyimpan Pencarian.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deletePreference(preference.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["preferences"] });
      queryClient.removeQueries({ queryKey: ["preference", preference.id] });
      toast.info("Pencarian dihapus.");
      navigate({ to: "/preferences" });
    },
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    updateMutation.mutate(values);
  }

  const initialValues = buildInitialValues(preference);
  const isDirty =
    values.title !== initialValues.title ||
    !arraysEqual(values.job_type, initialValues.job_type) ||
    !arraysEqual(values.remote_option, initialValues.remote_option);

  function handleDiscard() {
    if (isDirty) {
      const ok = window.confirm("Buang perubahan yang belum disimpan?");
      if (!ok) return;
    }
    setValues(initialValues);
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      {isRunning && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
        >
          <span className="font-semibold">Perhatian —</span>
          <span>
            Pencarian ini lagi berjalan. Menyimpan akan menjeda crawl dan
            dikirim ulang ke admin untuk ditinjau sebelum berjalan lagi.
          </span>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Ubah Pencarian</CardTitle>
          <CardDescription>
            Dibuat{" "}
            {new Date(preference.created_on).toLocaleDateString("id-ID", {
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PreferenceFormFields
            values={values}
            onChange={setValues}
            disabled={updateMutation.isPending}
          />
          {error && <p className="mt-4 text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        {canDelete ? (
          <DeleteDialog
            preference={preference}
            isDeleting={deleteMutation.isPending}
            onConfirm={() => deleteMutation.mutate()}
          />
        ) : (
          <span />
        )}
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={updateMutation.isPending || !isDirty}
            onClick={handleDiscard}
          >
            Buang perubahan
          </Button>
          <Button type="submit" disabled={updateMutation.isPending}>
            {updateMutation.isPending
              ? "Menyimpan…"
              : isRunning
                ? "Kirim perubahan untuk ditinjau"
                : "Simpan perubahan"}
          </Button>
        </div>
      </div>
    </form>
  );
}
