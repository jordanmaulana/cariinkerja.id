import * as React from "react"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { JOB_TYPES, REMOTE_OPTIONS } from "@/lib/consts"
import {
  PREFERENCE_SOURCES,
  PREFERENCE_STATUSES,
  type Preference,
  type PreferencePayload,
} from "@/lib/preferences"

export type PreferenceFormValues = {
  title: string
  job_type: string
  remote_option: string
  crawl_url: string
  crawl_source: string
  status: string
}

export function buildInitialValues(p?: Preference | null): PreferenceFormValues {
  return {
    title: p?.title ?? "",
    job_type: p?.job_type ?? "",
    remote_option: p?.remote_option ?? "",
    crawl_url: p?.crawl_url ?? "",
    crawl_source: p?.crawl_source ?? "",
    status: p?.status ?? "waiting_payment",
  }
}

export function valuesToPayload(v: PreferenceFormValues): PreferencePayload {
  return {
    title: v.title.trim() || null,
    job_type: (v.job_type || null) as PreferencePayload["job_type"],
    remote_option: (v.remote_option || null) as PreferencePayload["remote_option"],
    crawl_url: v.crawl_url.trim() || null,
    crawl_source: (v.crawl_source || null) as PreferencePayload["crawl_source"],
    status: (v.status || "waiting_payment") as PreferencePayload["status"],
  }
}

type Props = {
  values: PreferenceFormValues
  onChange: (values: PreferenceFormValues) => void
  showStatus?: boolean
  disabled?: boolean
}

export function PreferenceFormFields({
  values,
  onChange,
  showStatus = false,
  disabled,
}: Props) {
  function update<K extends keyof PreferenceFormValues>(
    key: K,
    value: PreferenceFormValues[K],
  ) {
    onChange({ ...values, [key]: value })
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field className="sm:col-span-2" label="Title" htmlFor="pref-title">
        <Input
          id="pref-title"
          value={values.title}
          disabled={disabled}
          onChange={(e) => update("title", e.target.value)}
          placeholder="e.g. Senior Backend Engineer"
        />
      </Field>

      <Field label="Job type" htmlFor="pref-job-type">
        <Select
          value={values.job_type}
          onValueChange={(v) => update("job_type", v)}
          disabled={disabled}
        >
          <SelectTrigger id="pref-job-type">
            <SelectValue placeholder="Any" />
          </SelectTrigger>
          <SelectContent>
            {JOB_TYPES.map((j) => (
              <SelectItem key={j.value} value={j.value}>
                {j.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>

      <Field label="Remote" htmlFor="pref-remote">
        <Select
          value={values.remote_option}
          onValueChange={(v) => update("remote_option", v)}
          disabled={disabled}
        >
          <SelectTrigger id="pref-remote">
            <SelectValue placeholder="Any" />
          </SelectTrigger>
          <SelectContent>
            {REMOTE_OPTIONS.map((r) => (
              <SelectItem key={r.value} value={r.value}>
                {r.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>

      <Field
        className="sm:col-span-2"
        label="Crawl URL"
        htmlFor="pref-crawl-url"
        hint="Listing URL for Indeed or JobStreet — admin uses this to crawl jobs."
      >
        <Input
          id="pref-crawl-url"
          type="url"
          value={values.crawl_url}
          disabled={disabled}
          onChange={(e) => update("crawl_url", e.target.value)}
          placeholder="https://"
        />
      </Field>

      <Field label="Crawl source" htmlFor="pref-crawl-source">
        <Select
          value={values.crawl_source}
          onValueChange={(v) => update("crawl_source", v)}
          disabled={disabled}
        >
          <SelectTrigger id="pref-crawl-source">
            <SelectValue placeholder="Unset" />
          </SelectTrigger>
          <SelectContent>
            {PREFERENCE_SOURCES.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>

      {showStatus && (
        <Field label="Status" htmlFor="pref-status">
          <Select
            value={values.status}
            onValueChange={(v) => update("status", v)}
            disabled={disabled}
          >
            <SelectTrigger id="pref-status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PREFERENCE_STATUSES.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      )}
    </div>
  )
}

function Field({
  label,
  htmlFor,
  hint,
  className,
  children,
}: {
  label: string
  htmlFor: string
  hint?: string
  className?: string
  children: React.ReactNode
}) {
  return (
    <div className={["space-y-1.5", className].filter(Boolean).join(" ")}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}
