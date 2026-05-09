import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "react-toastify";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  buildInitialValues,
  PreferenceFormFields,
  type PreferenceFormValues,
  valuesToPayload,
} from "@/features/preferences/components/preference-form";
import { createPreference } from "@/features/preferences/api";
import type { Preference } from "@/features/preferences/types";

export function NewPreferenceDialog() {
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<PreferenceFormValues>(buildInitialValues());
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (v: PreferenceFormValues) => createPreference(valuesToPayload(v)),
    onSuccess: (created) => {
      queryClient.setQueryData<Preference[] | undefined>(
        ["preferences"],
        (prev) => (prev ? [created, ...prev] : [created]),
      );
      queryClient.invalidateQueries({ queryKey: ["preferences"] });
      setOpen(false);
      setValues(buildInitialValues());
      toast.success(
        `Pencarian “${created.title || "Tanpa judul"}” dibuat. Admin akan meninjau berikutnya.`,
      );
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Gagal membuat Pencarian.");
    },
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!values.title.trim()) {
      setError("Judul wajib diisi.");
      return;
    }
    mutation.mutate(values);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) {
          setValues(buildInitialValues());
          setError(null);
        }
      }}
    >
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="size-4" />
          Pencarian Baru
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={onSubmit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>Pencarian Baru</DialogTitle>
            <DialogDescription>
              Tentukan apa yang kamu mau. Detail crawl bisa ditambah nanti.
            </DialogDescription>
          </DialogHeader>
          <PreferenceFormFields
            values={values}
            onChange={setValues}
            disabled={mutation.isPending}
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={mutation.isPending}>
                Batal
              </Button>
            </DialogClose>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Membuat…" : "Buat"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
