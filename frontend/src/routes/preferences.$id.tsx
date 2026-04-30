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
            Back to preferences
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
            Failed to load preference. It may not exist.
          </CardContent>
        </Card>
      )}

      {query.data && <PreferenceEditor key={query.data.id} preference={query.data} />}
    </div>
  )
}

function PreferenceEditor({ preference }: { preference: Preference }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [values, setValues] = useState<PreferenceFormValues>(() =>
    buildInitialValues(preference),
  )
  const [error, setError] = useState<string | null>(null)

  const updateMutation = useMutation({
    mutationFn: (v: PreferenceFormValues) =>
      updatePreference(preference.id, valuesToPayload(v)),
    onSuccess: (updated) => {
      queryClient.setQueryData(["preference", preference.id], updated)
      queryClient.invalidateQueries({ queryKey: ["preferences"] })
      setValues(buildInitialValues(updated))
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Failed to save preference.")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deletePreference(preference.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["preferences"] })
      queryClient.removeQueries({ queryKey: ["preference", preference.id] })
      navigate({ to: "/preferences" })
    },
  })

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    updateMutation.mutate(values)
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Edit preference</CardTitle>
          <CardDescription>
            Created{" "}
            {new Date(preference.created_on).toLocaleDateString(undefined, {
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
            showStatus
            disabled={updateMutation.isPending}
          />
          {error && <p className="mt-4 text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <DeleteDialog
          preference={preference}
          isDeleting={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate()}
        />
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={updateMutation.isPending}
            onClick={() => setValues(buildInitialValues(preference))}
          >
            Reset
          </Button>
          <Button type="submit" disabled={updateMutation.isPending}>
            {updateMutation.isPending ? "Saving…" : "Save changes"}
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
          Delete
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete preference?</DialogTitle>
          <DialogDescription>
            This removes “{preference.title || "Untitled"}” and any assessments
            tied to it. Cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="outline" disabled={isDeleting}>
              Cancel
            </Button>
          </DialogClose>
          <Button
            type="button"
            variant="destructive"
            disabled={isDeleting}
            onClick={onConfirm}
          >
            {isDeleting ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
