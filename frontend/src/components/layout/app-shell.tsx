import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useAtom, useSetAtom } from "jotai";
import {
  ClipboardCheck,
  CreditCard,
  LayoutDashboard,
  LogOut,
  MessageCircle,
  SlidersHorizontal,
} from "lucide-react";

import { LogoMark } from "@/components/brand/logo-mark";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { logout } from "@/features/auth/api";
import { tokenAtom, userAtom } from "@/features/auth/state";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/assessments", label: "Loker Tersedia", icon: ClipboardCheck },
  { to: "/preferences", label: "Pencarian", icon: SlidersHorizontal },
  { to: "/plans", label: "Paket", icon: CreditCard },
] as const;

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/assessments": "Loker Tersedia",
  "/preferences": "Pencarian",
  "/plans": "Paket",
};

function pageTitle(pathname: string) {
  const exact = PAGE_TITLES[pathname];
  if (exact) return exact;
  const match = Object.keys(PAGE_TITLES).find((k) => pathname.startsWith(k));
  return match ? PAGE_TITLES[match] : "";
}

function initialsOf(user: { email: string; full_name: string | null }) {
  const src = user.full_name || user.email;
  const parts = src.trim().split(/\s+|@/).filter(Boolean);
  const first = parts[0]?.[0] ?? "";
  const second = parts.length > 1 ? parts[1][0] : "";
  return (first + second).toUpperCase() || "U";
}

export function AppShell() {
  const [user, setUser] = useAtom(userAtom);
  const setToken = useSetAtom(tokenAtom);
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  async function onLogout() {
    await logout();
    setUser(null);
    setToken(null);
    navigate({ to: "/login" });
  }

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="hidden w-60 shrink-0 flex-col border-r bg-card md:flex">
        <div className="flex h-14 items-center gap-2 border-b px-5">
          <LogoMark className="size-5 text-primary" />
          <span className="text-sm font-semibold tracking-tight">
            cariinkerja<span className="opacity-60">.id</span>
          </span>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          {NAV.map(({ to, label, icon: Icon }) => {
            const active =
              pathname === to || pathname.startsWith(`${to}/`);
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  active && "bg-muted text-foreground",
                )}
              >
                <Icon className="size-4" />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b bg-background/80 px-4 backdrop-blur md:px-8">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="truncate text-base font-semibold">
              {pageTitle(pathname)}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex h-8 items-center gap-2 rounded-full border bg-background pl-1 pr-3 text-xs font-medium transition-colors hover:bg-muted"
                  aria-label="Menu pengguna"
                >
                  <span className="grid size-6 place-items-center rounded-full bg-muted text-[10px] font-semibold uppercase text-foreground">
                    {user ? initialsOf(user) : "?"}
                  </span>
                  <span className="hidden max-w-[14ch] truncate sm:block">
                    {user?.full_name || user?.email || "Akun"}
                  </span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                {user && (
                  <>
                    <DropdownMenuLabel>
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium text-foreground">
                          {user.full_name || "Akun"}
                        </div>
                        <div className="truncate text-xs text-muted-foreground">
                          {user.email}
                        </div>
                      </div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                  </>
                )}
                <DropdownMenuItem onSelect={onLogout}>
                  <LogOut className="size-4" />
                  Keluar
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <main className="flex-1 px-4 py-6 md:px-8 md:py-8">
          <div className="mx-auto w-full max-w-7xl">
            <Outlet />
          </div>
        </main>
        <footer className="border-t px-4 py-4 md:px-8">
          <div className="mx-auto flex w-full max-w-7xl items-center justify-center gap-2 text-xs text-muted-foreground">
            <span>Butuh bantuan? Hubungi admin via</span>
            <a
              href="https://wa.me/6285138530082"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 font-medium text-foreground transition-colors hover:text-primary"
            >
              <MessageCircle className="size-3.5" />
              WhatsApp
            </a>
          </div>
        </footer>
      </div>
    </div>
  );
}
