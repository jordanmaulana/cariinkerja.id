import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSetAtom } from "jotai";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { signup } from "@/lib/auth";
import { tokenAtom, userAtom } from "@/state/atoms";

export const Route = createFileRoute("/signup")({
  component: SignupPage,
});

function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const setToken = useSetAtom(tokenAtom);
  const setUser = useSetAtom(userAtom);
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await signup({ email, password });
      setToken(res.token);
      setUser(res.user);
      navigate({ to: "/onboarding" });
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "Signup failed. Try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-sm p-8 space-y-6">
      <h1 className="text-2xl font-bold">Sign up</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="email" className="text-sm font-medium">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded border px-3 py-2"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="password" className="text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded border px-3 py-2"
          />
          <p className="text-xs text-muted-foreground">Min 8 characters.</p>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? "Creating…" : "Create account"}
        </Button>
      </form>
      <p className="text-sm text-muted-foreground">
        Already have an account?{" "}
        <a href="/login" className="underline">
          Log in
        </a>
      </p>
    </main>
  );
}
