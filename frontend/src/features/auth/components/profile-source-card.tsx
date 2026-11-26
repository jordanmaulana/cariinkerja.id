import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ProfileMe } from "@/features/auth/types";
import { formatDateTime } from "@/lib/utils";

export function ProfileSourceCard({ profile }: { profile: ProfileMe }) {
  const isCv = profile.cv_text !== null;
  const ingested = profile.linkedin_ingested_at;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          Sumber profil
          <Badge variant="outline">{isCv ? "CV (PDF)" : "LinkedIn"}</Badge>
        </CardTitle>
        <CardDescription>
          AI menilai tiap loker terhadap isi profil ini.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {!isCv && profile.linkedin_url && (
          <div className="space-y-1">
            <a
              href={profile.linkedin_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
            >
              {profile.linkedin_url}
              <ExternalLink className="size-3.5" />
            </a>
            <p className="text-xs text-muted-foreground">
              Diambil otomatis dari LinkedIn-mu. Kalau kamu baru update
              LinkedIn, hubungi admin biar kami ambil ulang.
            </p>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted-foreground">Status AI:</span>
          {!ingested ? (
            <Badge variant="secondary">Belum diproses</Badge>
          ) : profile.linkedin_quality_ok ? (
            <Badge>Siap dinilai</Badge>
          ) : (
            <Badge variant="destructive">Perlu dilengkapi</Badge>
          )}
          {ingested && (
            <span className="text-xs text-muted-foreground">
              diproses {formatDateTime(ingested)}
            </span>
          )}
        </div>
        {ingested && !profile.linkedin_quality_ok && profile.linkedin_quality_reason && (
          <p className="text-muted-foreground">{profile.linkedin_quality_reason}</p>
        )}
      </CardContent>
    </Card>
  );
}
