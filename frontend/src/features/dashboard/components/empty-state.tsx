import { Link } from "@tanstack/react-router";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-start gap-3 py-10">
        <div>
          <h3 className="text-base font-semibold">Belum ada penilaian</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Tambah Pencarian untuk mulai mengambil loker dan menghasilkan
            kecocokan.
          </p>
        </div>
        <Button asChild size="sm">
          <Link to="/preferences">Kelola Pencarian</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
