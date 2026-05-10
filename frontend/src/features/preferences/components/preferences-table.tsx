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
import { JOB_TYPE_LABEL, REMOTE_LABEL } from "@/features/jobs/consts";
import { STATUS_LABEL, STATUS_VARIANT } from "@/features/preferences/consts";
import type { Preference } from "@/features/preferences/types";

type Props = {
  rows: Preference[];
  onRowClick: (id: string) => void;
};

export function PreferencesTable({ rows, onRowClick }: Props) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Judul</TableHead>
          <TableHead>Tipe</TableHead>
          <TableHead>Remote</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Dibuat</TableHead>
          <TableHead></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((p) => (
          <TableRow
            key={p.id}
            className="cursor-pointer"
            onClick={() => onRowClick(p.id)}
          >
            <TableCell>
              <span className="font-medium">{p.title || "—"}</span>
            </TableCell>
            <TableCell>
              {p.job_type.length
                ? p.job_type.map((v) => JOB_TYPE_LABEL[v]).join(", ")
                : "Semua"}
            </TableCell>
            <TableCell>
              {p.remote_option.length
                ? p.remote_option.map((v) => REMOTE_LABEL[v]).join(", ")
                : "Semua"}
            </TableCell>
            <TableCell>
              <Badge variant={STATUS_VARIANT[p.status]}>
                {STATUS_LABEL[p.status]}
              </Badge>
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">
              {new Date(p.created_on).toLocaleDateString("id-ID", {
                day: "2-digit",
                month: "short",
              })}
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
  );
}
