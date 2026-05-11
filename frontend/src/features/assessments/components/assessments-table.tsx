import { Link } from "@tanstack/react-router";

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
import { ConfirmActionButton } from "@/features/assessments/components/confirm-action-button";
import { getActionsForStatus } from "@/features/assessments/actions";
import {
  STATUS_HINT,
  STATUS_LABEL,
  STATUS_VARIANT,
} from "@/features/assessments/consts";
import type {
  Assessment,
  AssessmentStatus,
} from "@/features/assessments/types";
import { JOB_TYPE_LABEL, REMOTE_LABEL } from "@/features/jobs/consts";
import type { AssessmentsSearch } from "@/routes/assessments.index";

type Props = {
  rows: Assessment[];
  isPending: boolean;
  pendingId?: string;
  fromSearch: AssessmentsSearch;
  onAction: (id: string, next: AssessmentStatus) => void;
  onOpen: (id: string) => void;
};

export function AssessmentsTable({
  rows,
  isPending,
  pendingId,
  fromSearch,
  onAction,
  onOpen,
}: Props) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Loker</TableHead>
          <TableHead>Perusahaan</TableHead>
          <TableHead>Tipe</TableHead>
          <TableHead>Remote</TableHead>
          <TableHead className="text-right">Skor</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Tanggal</TableHead>
          <TableHead className="text-right">Aksi</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => {
          const actions = getActionsForStatus(row.status);
          const rowPending = isPending && pendingId === row.id;
          const created = new Date(row.created_on).toLocaleDateString("id-ID", {
            day: "2-digit",
            month: "short",
          });
          return (
            <TableRow
              key={row.id}
              className="cursor-pointer"
              onClick={(e) => {
                if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1)
                  return;
                if (row.status === "new") onAction(row.id, "seen");
                onOpen(row.id);
              }}
            >
              <TableCell className="max-w-[280px]">
                <Link
                  to="/assessments/$id"
                  params={{ id: row.id }}
                  state={{ fromSearch } as never}
                  className="block truncate font-medium hover:underline"
                  title={row.job.title}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (row.status === "new") onAction(row.id, "seen");
                  }}
                >
                  {row.job.title}
                </Link>
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
              <TableCell className="text-right font-medium tabular-nums">
                {row.score}
              </TableCell>
              <TableCell>
                <Badge
                  variant={STATUS_VARIANT[row.status]}
                  title={STATUS_HINT[row.status]}
                >
                  {STATUS_LABEL[row.status]}
                </Badge>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {created}
              </TableCell>
              <TableCell
                className="space-x-1.5 text-right"
                onClick={(e) => e.stopPropagation()}
              >
                {actions.length === 0 && (
                  <span
                    className="text-xs text-muted-foreground"
                    title="Status final — tidak ada aksi lebih lanjut."
                  >
                    —
                  </span>
                )}
                {actions.map((a) =>
                  a.confirm ? (
                    <ConfirmActionButton
                      key={a.next}
                      action={a}
                      disabled={rowPending}
                      onConfirm={() => onAction(row.id, a.next)}
                    />
                  ) : (
                    <Button
                      key={a.next}
                      size="xs"
                      variant={a.variant ?? "default"}
                      disabled={rowPending}
                      onClick={() => onAction(row.id, a.next)}
                    >
                      {a.label}
                    </Button>
                  ),
                )}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
