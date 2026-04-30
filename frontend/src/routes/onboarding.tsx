import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSetAtom } from "jotai";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { submitOnboarding } from "@/lib/auth";
import { JOB_TYPES, REMOTE_OPTIONS } from "@/lib/consts";
import type { JobType, RemoteOption } from "@/lib/consts";
import { userAtom } from "@/state/atoms";

export const Route = createFileRoute("/onboarding")({
  component: OnboardingPage,
});

function OnboardingPage() {
  const [fullName, setFullName] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [bio, setBio] = useState("");
  const [title, setTitle] = useState("");
  const [jobType, setJobType] = useState<JobType>(JOB_TYPES[0].value);
  const [remoteOption, setRemoteOption] = useState<RemoteOption>(
    REMOTE_OPTIONS[0].value,
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const setUser = useSetAtom(userAtom);
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await submitOnboarding({
        full_name: fullName,
        linkedin_url: linkedinUrl || undefined,
        bio: bio || undefined,
        title,
        job_type: jobType,
        remote_option: remoteOption,
      });
      setUser((prev) =>
        prev ? { ...prev, full_name: fullName, onboarded: true } : prev,
      );
      navigate({ to: "/" });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Could not save. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Tell us about you</h1>
        <p className="text-sm text-muted-foreground">
          Fill your profile and your first job preference to get started.
        </p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4">
        <fieldset className="space-y-4">
          <legend className="text-sm font-semibold">Profile</legend>
          <div className="space-y-1">
            <label htmlFor="full_name" className="text-sm font-medium">
              Full name
            </label>
            <input
              id="full_name"
              required
              autoFocus
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded border px-3 py-2"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="linkedin_url" className="text-sm font-medium">
              LinkedIn URL
            </label>
            <input
              id="linkedin_url"
              type="url"
              placeholder="https://linkedin.com/in/..."
              value={linkedinUrl}
              onChange={(e) => setLinkedinUrl(e.target.value)}
              className="w-full rounded border px-3 py-2"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="bio" className="text-sm font-medium">
              Bio
            </label>
            <textarea
              id="bio"
              rows={3}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              className="w-full rounded border px-3 py-2"
            />
          </div>
        </fieldset>

        <fieldset className="space-y-4">
          <legend className="text-sm font-semibold">First preference</legend>
          <div className="space-y-1">
            <label htmlFor="title" className="text-sm font-medium">
              Job title
            </label>
            <input
              id="title"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded border px-3 py-2"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="job_type" className="text-sm font-medium">
              Job type
            </label>
            <select
              id="job_type"
              value={jobType}
              onChange={(e) => setJobType(e.target.value as JobType)}
              className="w-full rounded border px-3 py-2"
            >
              {JOB_TYPES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label htmlFor="remote_option" className="text-sm font-medium">
              Remote option
            </label>
            <select
              id="remote_option"
              value={remoteOption}
              onChange={(e) => setRemoteOption(e.target.value as RemoteOption)}
              className="w-full rounded border px-3 py-2"
            >
              {REMOTE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </fieldset>

        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? "Saving…" : "Finish onboarding"}
        </Button>
      </form>
    </main>
  );
}
