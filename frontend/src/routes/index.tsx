import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useAtom, useSetAtom } from "jotai";

import { Button } from "@/components/ui/button";
import { logout } from "@/lib/auth";
import { tokenAtom, userAtom } from "@/state/atoms";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  const [user, setUser] = useAtom(userAtom);
  const setToken = useSetAtom(tokenAtom);
  const navigate = useNavigate();

  async function onLogout() {
    await logout();
    setUser(null);
    setToken(null);
    navigate({ to: "/login" });
  }

  return (
    <main className="p-8 space-y-4">
      <h1 className="text-2xl font-bold">cariinkerja.id</h1>
      {user && (
        <p className="text-sm text-muted-foreground">
          Signed in as <span className="font-medium">{user.email}</span>
          {user.full_name ? ` — ${user.full_name}` : ""}
        </p>
      )}
      <div className="flex gap-2">
        <Link to="/assessments">
          <Button>View assessments</Button>
        </Link>
        <Button onClick={onLogout} variant="outline">
          Log out
        </Button>
      </div>
    </main>
  );
}
