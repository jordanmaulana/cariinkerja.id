import { LogoLockup } from "@/components/brand/logo-mark";
import { BEFORE_YOU_BUY, LOGIN_FEATURES } from "@/features/auth/consts";

export function LoginSidePanel() {
  return (
    <section className="hidden lg:flex flex-col justify-between p-12 border-r border-border bg-muted/30 relative overflow-hidden">
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none opacity-60 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, color-mix(in oklch, var(--border) 100%, transparent) 1px, transparent 0)",
          backgroundSize: "20px 20px",
        }}
      />
      <div className="relative">
        <LogoLockup />
        <div className="mt-8 rounded-md border border-border bg-card/40 p-5 max-w-md">
          <h2 className="text-sm font-semibold tracking-tight">
            Sebelum kamu beli
          </h2>
          <ol className="mt-3 space-y-2 text-sm text-muted-foreground list-decimal list-inside">
            {BEFORE_YOU_BUY.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
        </div>
      </div>
      <div className="relative">
        <h2 className="font-heading text-3xl xl:text-4xl font-semibold tracking-tight leading-tight">
          Cariin kamu loker yang cocok, biar kamu ga capek cari sendiri.
        </h2>
        <p className="mt-3 text-muted-foreground text-base max-w-md">
          Manfaatin waktu luangmu buat upgrade skill yang kamu butuhin dari loker yang kamu pilih / yaudah terserah mau tidur kek apalah.
        </p>
        <ul className="mt-10 space-y-6">
          {LOGIN_FEATURES.map(({ icon: Icon, title, body }) => (
            <li key={title} className="flex gap-4 items-start">
              <div className="size-9 shrink-0 rounded-md border border-border bg-card grid place-items-center">
                <Icon className="size-4" aria-hidden />
              </div>
              <div>
                <p className="text-sm font-medium">{title}</p>
                <p className="text-sm text-muted-foreground">{body}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
      <p className="relative text-xs text-muted-foreground">
        Dibuat untuk pencari kerja Indonesia. © 2026 cariinkerja.id
      </p>
    </section>
  );
}

export function LoginMobilePrechecklist() {
  return (
    <div className="mt-6 lg:hidden rounded-md border border-border bg-muted/30 p-5">
      <h2 className="text-sm font-semibold tracking-tight">Sebelum kamu beli</h2>
      <ol className="mt-3 space-y-2 text-sm text-muted-foreground list-decimal list-inside">
        {BEFORE_YOU_BUY.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ol>
    </div>
  );
}
