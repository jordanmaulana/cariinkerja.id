import * as React from "react"

import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { JOB_TYPES, REMOTE_OPTIONS, type JobType, type RemoteOption } from "@/lib/consts"
import { type Preference, type PreferencePayload } from "@/lib/preferences"

export type PreferenceFormValues = {
  title: string
  job_type: JobType[]
  remote_option: RemoteOption[]
}

export function buildInitialValues(p?: Preference | null): PreferenceFormValues {
  return {
    title: p?.title ?? "",
    job_type: p?.job_type ?? [],
    remote_option: p?.remote_option ?? [],
  }
}

export function valuesToPayload(v: PreferenceFormValues): PreferencePayload {
  return {
    title: v.title.trim() || null,
    job_type: v.job_type,
    remote_option: v.remote_option,
  }
}

type Props = {
  values: PreferenceFormValues
  onChange: (values: PreferenceFormValues) => void
  disabled?: boolean
}

export function PreferenceFormFields({ values, onChange, disabled }: Props) {
  function update<K extends keyof PreferenceFormValues>(
    key: K,
    value: PreferenceFormValues[K],
  ) {
    onChange({ ...values, [key]: value })
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field className="sm:col-span-2" label="Judul" htmlFor="pref-title">
        <Input
          id="pref-title"
          value={values.title}
          disabled={disabled}
          onChange={(e) => update("title", e.target.value)}
          placeholder="cth. Senior Backend Engineer"
        />
      </Field>

      <Field label="Tipe pekerjaan" htmlFor="pref-job-type">
        <CheckboxGroup<JobType>
          name="pref-job-type"
          options={JOB_TYPES}
          values={values.job_type}
          disabled={disabled}
          onChange={(next) => update("job_type", next)}
        />
        <p className="text-xs text-muted-foreground">Kosongin = semua tipe</p>
      </Field>

      <Field label="Remote" htmlFor="pref-remote">
        <CheckboxGroup<RemoteOption>
          name="pref-remote"
          options={REMOTE_OPTIONS}
          values={values.remote_option}
          disabled={disabled}
          onChange={(next) => update("remote_option", next)}
        />
        <p className="text-xs text-muted-foreground">Kosongin = semua opsi</p>
      </Field>
    </div>
  )
}

type CheckboxGroupProps<T extends string> = {
  name: string
  options: ReadonlyArray<{ value: T; label: string }>
  values: T[]
  disabled?: boolean
  onChange: (next: T[]) => void
}

function CheckboxGroup<T extends string>({
  name,
  options,
  values,
  disabled,
  onChange,
}: CheckboxGroupProps<T>) {
  function toggle(value: T, checked: boolean) {
    if (checked) {
      if (values.includes(value)) return
      const ordered = options.map((o) => o.value).filter((v) => values.includes(v) || v === value)
      onChange(ordered)
    } else {
      onChange(values.filter((v) => v !== value))
    }
  }

  return (
    <div className="flex flex-wrap gap-x-4 gap-y-2">
      {options.map((opt) => {
        const id = `${name}-${opt.value}`
        const checked = values.includes(opt.value)
        return (
          <label
            key={opt.value}
            htmlFor={id}
            className="inline-flex items-center gap-2 text-sm cursor-pointer select-none"
          >
            <Checkbox
              id={id}
              checked={checked}
              disabled={disabled}
              onCheckedChange={(state) => toggle(opt.value, state === true)}
            />
            {opt.label}
          </label>
        )
      })}
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
