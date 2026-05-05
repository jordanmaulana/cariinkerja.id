import { useState } from "react"
import { Link, createFileRoute, useNavigate } from "@tanstack/react-router"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"

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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { JOB_TYPES, REMOTE_OPTIONS } from "@/lib/consts"
import {
  createPreference,
  listPreferences,
  PREFERENCE_STATUSES,
  type Preference,
  type PreferenceStatus,
} from "@/lib/preferences"
import { toast } from "react-toastify"

export const Route = createFileRoute("/preferences/")({
  component: PreferencesPage,
})

const JOB_TYPE_LABEL = Object.fromEntries(
  JOB_TYPES.map((j) => [j.value, j.label]),
)
const REMOTE_LABEL = Object.fromEntries(
  REMOTE_OPTIONS.map((r) => [r.value, r.label]),
)
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

function PreferencesPage() {
  const navigate = useNavigate()
  const query = useQuery({
    queryKey: ["preferences"],
    queryFn: listPreferences,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">Pencarian</h2>
          <p className="text-sm text-muted-foreground">
            Tentukan apa yang kamu mau. Tiap Pencarian jadi feed crawl +
            kecocokan.
          </p>
        </div>
        <NewPreferenceDialog />
      </div>

      <PaymentGateBanner />

      <Card>
        <CardHeader>
          <CardTitle>Pencarianmu</CardTitle>
          <CardDescription>
            {query.data?.length ?? 0} total
          </CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          {query.isLoading && (
            <div className="px-6 pb-6">
              <Skeleton className="h-32 w-full" />
            </div>
          )}
          {query.isError && (
            <div className="px-6 pb-6 text-sm text-destructive">
              Gagal memuat Pencarian.
            </div>
          )}
          {query.data && query.data.length === 0 && (
            <div className="px-6 pb-6 text-sm text-muted-foreground">
              Belum ada Pencarian. Tambah satu untuk mulai crawling.
            </div>
          )}
          {query.data && query.data.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Judul</TableHead>
                  <TableHead>Tipe</TableHead>
                  <TableHead>Remote</TableHead>
                  <TableHead>Sumber</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Dibuat</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {query.data.map((p) => (
                  <TableRow
                    key={p.id}
                    className="cursor-pointer"
                    onClick={() =>
                      navigate({
                        to: "/preferences/$id",
                        params: { id: p.id },
                      })
                    }
                  >
                    <TableCell>
                      <span className="font-medium">{p.title || "—"}</span>
                    </TableCell>
                    <TableCell>
                      {p.job_type ? JOB_TYPE_LABEL[p.job_type] : "—"}
                    </TableCell>
                    <TableCell>
                      {p.remote_option ? REMOTE_LABEL[p.remote_option] : "—"}
                    </TableCell>
                    <TableCell className="capitalize">
                      {p.crawl_source ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[p.status]}>
                        {STATUS_LABEL[p.status]}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(p.created_on).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {p.status === "waiting_payment" && (
                        <Button
                          asChild
                          size="sm"
                          variant="outline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Link to="/plans">Pilih paket</Link>
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function NewPreferenceDialog() {
  const [open, setOpen] = useState(false)
  const [values, setValues] = useState<PreferenceFormValues>(buildInitialValues())
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (v: PreferenceFormValues) => {
      const payload = valuesToPayload(v)
      // Backend ignores status on create unless provided; default value handles it.
      return createPreference(payload)
    },
    onSuccess: (created) => {
      queryClient.setQueryData<Preference[] | undefined>(
        ["preferences"],
        (prev) => (prev ? [created, ...prev] : [created]),
      )
      queryClient.invalidateQueries({ queryKey: ["preferences"] })
      setOpen(false)
      setValues(buildInitialValues())
      toast.success(
        `Pencarian “${created.title || "Tanpa judul"}” dibuat. Admin akan meninjau berikutnya.`,
      )
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Gagal membuat Pencarian.")
    },
  })

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!values.title.trim()) {
      setError("Judul wajib diisi.")
      return
    }
    mutation.mutate(values)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        if (!o) {
          setValues(buildInitialValues())
          setError(null)
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
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
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
  )
}
