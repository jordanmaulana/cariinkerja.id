import { useState } from "react";
import {
  createFileRoute,
  Link,
  useNavigate,
} from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  type Assessment,
  type AssessmentStatus,
  ASSESSMENT_STATUSES,
  listAssessments,
  updateAssessmentStatus,
} from "@/lib/assessments";
import { JOB_TYPES, REMOTE_OPTIONS } from "@/lib/consts";

export const Route = createFileRoute("/assessments/")({
  component: AssessmentsPage,
});

type TabValue = "all" | AssessmentStatus;

const TAB_LABELS: Record<TabValue, string> = {
  all: "All",
  new: "New",
  seen: "Seen",
  applied: "Applied",
  rejected: "Rejected",
  accepted: "Accepted",
};

const STATUS_VARIANT: Record<
  AssessmentStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  new: "secondary",
  seen: "outline",
  applied: "default",
  rejected: "destructive",
  accepted: "default",
};

const JOB_TYPE_LABEL = Object.fromEntries(
  JOB_TYPES.map((j) => [j.value, j.label]),
);
const REMOTE_LABEL = Object.fromEntries(
  REMOTE_OPTIONS.map((r) => [r.value, r.label]),
);

type Action = {
  label: string;
  next: AssessmentStatus;
  variant?: "default" | "destructive" | "outline";
};

function getActionsForStatus(status: AssessmentStatus): Action[] {
  switch (status) {
    case "new":
      return [
        { label: "Mark Seen", next: "seen", variant: "outline" },
        { label: "Reject", next: "rejected", variant: "destructive" },
      ];
    case "seen":
      return [
        { label: "Mark Applied", next: "applied", variant: "default" },
        { label: "Reject", next: "rejected", variant: "destructive" },
      ];
    case "applied":
      return [
        { label: "Mark Accepted", next: "accepted", variant: "default" },
        { label: "Reject", next: "rejected", variant: "destructive" },
      ];
    default:
      return [];
  }
}

function AssessmentsPage() {
  const [tab, setTab] = useState<TabValue>("all");
  const [minScoreInput, setMinScoreInput] = useState("");
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const statusFilter = tab === "all" ? undefined : tab;
  const parsed = minScoreInput === "" ? undefined : Number(minScoreInput);
  const minScore =
    parsed != null && Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined;

  const query = useQuery({
    queryKey: ["assessments", tab, minScore ?? null],
    queryFn: () =>
      listAssessments({ status: statusFilter, minScore }),
  });

  const mutation = useMutation({
    mutationFn: ({ id, next }: { id: string; next: AssessmentStatus }) =>
      updateAssessmentStatus(id, next),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assessments"] });
    },
  });

  return (
    <main className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Assessments</h1>
        <Link to="/" className="text-sm text-muted-foreground hover:underline">
          ← Home
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <Tabs value={tab} onValueChange={(v) => setTab(v as TabValue)}>
          <TabsList>
            <TabsTrigger value="all">{TAB_LABELS.all}</TabsTrigger>
            {ASSESSMENT_STATUSES.map((s) => (
              <TabsTrigger key={s} value={s}>
                {TAB_LABELS[s]}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Min score</span>
          <input
            type="number"
            min={0}
            max={100}
            inputMode="numeric"
            placeholder="0"
            value={minScoreInput}
            onChange={(e) => setMinScoreInput(e.target.value)}
            className="h-8 w-20 rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          {minScoreInput !== "" && (
            <button
              type="button"
              onClick={() => setMinScoreInput("")}
              className="text-xs text-muted-foreground hover:underline"
            >
              clear
            </button>
          )}
        </label>
      </div>

      {query.isLoading && (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}
      {query.isError && (
        <p className="text-sm text-destructive">
          Failed to load assessments. Try refreshing.
        </p>
      )}

      {query.data && (
        <AssessmentsTable
          rows={query.data}
          isPending={mutation.isPending}
          pendingId={mutation.variables?.id}
          onAction={(id, next) => mutation.mutate({ id, next })}
          onOpen={(id) => navigate({ to: "/assessments/$id", params: { id } })}
        />
      )}
    </main>
  );
}

function AssessmentsTable({
  rows,
  isPending,
  pendingId,
  onAction,
  onOpen,
}: {
  rows: Assessment[];
  isPending: boolean;
  pendingId?: string;
  onAction: (id: string, next: AssessmentStatus) => void;
  onOpen: (id: string) => void;
}) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No assessments yet.</p>
    );
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Job</TableHead>
          <TableHead>Company</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Remote</TableHead>
          <TableHead>Score</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Assessed</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => {
          const actions = getActionsForStatus(row.status);
          const rowPending = isPending && pendingId === row.id;
          const created = new Date(row.created_on).toLocaleDateString();
          return (
            <TableRow
              key={row.id}
              className="cursor-pointer"
              onClick={() => onOpen(row.id)}
            >
              <TableCell>
                <span className="font-medium hover:underline">
                  {row.job.title}
                </span>
              </TableCell>
              <TableCell>
                <div className="font-medium">{row.job.company ?? "—"}</div>
                {row.job.location && (
                  <div className="text-xs text-muted-foreground">
                    {row.job.location}
                  </div>
                )}
              </TableCell>
              <TableCell>
                {row.job.job_type ? JOB_TYPE_LABEL[row.job.job_type] : "—"}
              </TableCell>
              <TableCell>
                {row.job.remote_option
                  ? REMOTE_LABEL[row.job.remote_option]
                  : "—"}
              </TableCell>
              <TableCell>{row.score}</TableCell>
              <TableCell>
                <Badge variant={STATUS_VARIANT[row.status]}>
                  {row.status}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground text-xs">
                {created}
              </TableCell>
              <TableCell
                className="text-right space-x-2"
                onClick={(e) => e.stopPropagation()}
              >
                {actions.length === 0 && (
                  <span className="text-xs text-muted-foreground">—</span>
                )}
                {actions.map((a) => (
                  <Button
                    key={a.next}
                    size="sm"
                    variant={a.variant ?? "default"}
                    disabled={rowPending}
                    onClick={() => onAction(row.id, a.next)}
                  >
                    {a.label}
                  </Button>
                ))}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
