import { useState } from "react"
import { Link, createFileRoute, useNavigate } from "@tanstack/react-router"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Trash2 } from "lucide-react"

import {
  buildInitialValues,
  PreferenceFormFields,
  type PreferenceFormValues,
  valuesToPayload,
} from "@/components/preference-form"
import { PaymentGateBanner } from "@/components/payment-gate-banner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import {
  PREFERENCE_STATUSES,
  type Preference,
  type PreferenceStatus,
  deletePreference,
  getPreference,
  updatePreference,
} from "@/lib/preferences"
import { toast } from "react-toastify"

export const Route = createFileRoute("/preferences/$id")({
  component: PreferenceDetailPage,
})

const STATUS_LABEL = Object.fromEntries(
  PREFERENCE_STATUSES.map((s) => [s.value, s.label]),
) as Record<PreferenceStatus, string>

const STATUS_VARIANT: Record<
  PreferenceStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  waiting_payment: "outline",
  waiting_admin: "secondary",
  running: "default",
  expired: "destructive",
}

function PreferenceDetailPage() {
  const { id } = Route.useParams()

  const query = useQuery({
    queryKey: ["preference", id],
    queryFn: () => getPreference(id),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link to="/preferences">
            <ArrowLeft className="size-4" />
            Kembali ke Pencarian
          </Link>
        </Button>
        {query.data && (
          <Badge variant={STATUS_VARIANT[query.data.status]}>
            {STATUS_LABEL[query.data.status]}
          </Badge>
        )}
      </div>

      {query.isLoading && <Skeleton className="h-96 w-full" />}
      {query.isError && (
        <Card>
          <CardContent className="py-6 text-sm text-destructive">
            Gagal memuat Pencarian. Mungkin tidak ada.
          </CardContent>
        </Card>
      )}

      {query.data && <StateNotice preference={query.data} />}
      <PaymentGateBanner />

      {query.data && <PreferenceEditor key={query.data.id} preference={query.data} />}
    </div>
  )
}

function StateNotice({ preference }: { preference: Preference }) {
  if (preference.status === "waiting_admin") {
    return (
      <Card className="border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950">
        <CardHeader>
          <CardTitle className="text-base text-amber-900 dark:text-amber-100">
            Lagi ngumpulin loker yang kamu cari
          </CardTitle>
          <CardDescription className="text-amber-900/80 dark:text-amber-100/80">
            Coba liat paketnya dulu biar nanti ga kaget lihat harga wkwkwk.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }
  if (preference.status === "waiting_payment") {
    return (
      <Card className="border-primary/40 bg-primary/5">
        <CardHeader className="flex-row items-center justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base">Pencarian disetujui</CardTitle>
            <CardDescription>
              Pilih paket untuk mulai mencocokkan loker.
            </CardDescription>
          </div>
          <Button asChild size="sm">
            <Link to="/plans">Pilih paket</Link>
          </Button>
        </CardHeader>
      </Card>
    )
  }
  return null
}

function PreferenceEditor({ preference }: { preference: Preference }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [values, setValues] = useState<PreferenceFormValues>(() =>
    buildInitialValues(preference),
  )
  const [error, setError] = useState<string | null>(null)
  const isRunning = preference.status === "running"
  const canDelete = preference.status === "waiting_payment"

  const updateMutation = useMutation({
    mutationFn: (v: PreferenceFormValues) =>
      updatePreference(preference.id, valuesToPayload(v)),
    onSuccess: (updated) => {
      const wasRunning = isRunning
      queryClient.setQueryData(["preference", preference.id], updated)
      queryClient.invalidateQueries({ queryKey: ["preferences"] })
      setValues(buildInitialValues(updated))
      if (wasRunning) {
        toast.warning(
          "Tersimpan. Crawl dijeda — dikirim ulang ke admin untuk ditinjau sebelum berjalan lagi.",
        )
      } else {
        toast.success("Pencarian diperbarui.")
      }
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Gagal menyimpan Pencarian.")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deletePreference(preference.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["preferences"] })
      queryClient.removeQueries({ queryKey: ["preference", preference.id] })
      toast.info("Pencarian dihapus.")
      navigate({ to: "/preferences" })
    },
  })

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    updateMutation.mutate(values)
  }

  const initialValues = buildInitialValues(preference)
  const isDirty =
    values.title !== initialValues.title ||
    values.job_type !== initialValues.job_type ||
    values.remote_option !== initialValues.remote_option

  function handleDiscard() {
    if (isDirty) {
      const ok = window.confirm("Buang perubahan yang belum disimpan?")
      if (!ok) return
    }
    setValues(initialValues)
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
  )
}

function DeleteDialog({
  preference,
  isDeleting,
  onConfirm,
}: {
  preference: Preference
  isDeleting: boolean
  onConfirm: () => void
}) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button type="button" variant="destructive">
          <Trash2 className="size-4" />
          Hapus
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Hapus Pencarian?</DialogTitle>
          <DialogDescription>
            Ini akan menghapus “{preference.title || "Tanpa judul"}” dan semua
            loker tersedia yang terkait. Tidak bisa dibatalkan.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="outline" disabled={isDeleting}>
              Batal
            </Button>
          </DialogClose>
          <Button
            type="button"
            variant="destructive"
            disabled={isDeleting}
            onClick={onConfirm}
          >
            {isDeleting ? "Menghapus…" : "Hapus"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
