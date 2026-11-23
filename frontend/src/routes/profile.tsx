import { createFileRoute } from "@tanstack/react-router";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CvEditor } from "@/features/auth/components/cv-editor";
import { ProfileSourceCard } from "@/features/auth/components/profile-source-card";
import { useProfile } from "@/features/auth/hooks";

export const Route = createFileRoute("/profile")({
  head: () => ({ meta: [{ title: "Profil — cariinkerja.id" }] }),
  component: ProfilePage,
});

function ProfilePage() {
  const { data: profile, isLoading, isError } = useProfile();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {isLoading && <Skeleton className="h-96 w-full" />}
      {isError && (
        <Card>
          <CardContent className="py-6 text-sm text-destructive">
            Gagal memuat profil.
          </CardContent>
        </Card>
      )}
      {profile && (
        <>
          <ProfileSourceCard profile={profile} />
          {profile.cv_text !== null && <CvEditor profile={profile} />}
        </>
      )}
    </div>
  );
}
