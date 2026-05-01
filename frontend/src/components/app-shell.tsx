import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router"
import { useAtom, useSetAtom } from "jotai"
import {
  ClipboardCheck,
  CreditCard,
  LayoutDashboard,
  LogOut,
  Moon,
  SlidersHorizontal,
  Sun,
} from "lucide-react"
import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { logout } from "@/lib/auth"
import { cn } from "@/lib/utils"
import { tokenAtom, userAtom } from "@/state/atoms"

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/assessments", label: "Available Jobs", icon: ClipboardCheck },
  { to: "/preferences", label: "Finder", icon: SlidersHorizontal },
  { to: "/plans", label: "Plans", icon: CreditCard },
] as const

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/assessments": "Available Jobs",
  "/preferences": "Finder",
  "/plans": "Plans",
}

const THEME_KEY = "theme"

function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") return "light"
    const stored = localStorage.getItem(THEME_KEY)
    if (stored === "dark" || stored === "light") return stored
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light"
  })
  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle("dark", theme === "dark")
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])
  return { theme, toggle: () => setTheme((t) => (t === "dark" ? "light" : "dark")) }
}

function pageTitle(pathname: string) {
  const exact = PAGE_TITLES[pathname]
  if (exact) return exact
  const match = Object.keys(PAGE_TITLES).find((k) => pathname.startsWith(k))
  return match ? PAGE_TITLES[match] : ""
}

function initialsOf(user: { email: string; full_name: string | null }) {
  const src = user.full_name || user.email
  const parts = src.trim().split(/\s+|@/).filter(Boolean)
  const first = parts[0]?.[0] ?? ""
  const second = parts.length > 1 ? parts[1][0] : ""
  return (first + second).toUpperCase() || "U"
}

export function AppShell() {
  const [user, setUser] = useAtom(userAtom)
  const setToken = useSetAtom(tokenAtom)
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const { theme, toggle } = useTheme()

  async function onLogout() {
    await logout()
    setUser(null)
    setToken(null)
    navigate({ to: "/login" })
  }

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="hidden w-60 shrink-0 flex-col border-r bg-card md:flex">
        <div className="flex h-14 items-center gap-2 border-b px-5">
          <span className="text-sm font-semibold tracking-tight">
            cariinkerja
          </span>
          <span className="text-xs text-muted-foreground">.id</span>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          {NAV.map(({ to, label, icon: Icon }) => {
            const active =
              pathname === to || pathname.startsWith(`${to}/`)
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
            )
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
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Toggle theme"
              onClick={toggle}
            >
              {theme === "dark" ? (
                <Sun className="size-4" />
              ) : (
                <Moon className="size-4" />
              )}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex h-8 items-center gap-2 rounded-full border bg-background pl-1 pr-3 text-xs font-medium transition-colors hover:bg-muted"
                  aria-label="User menu"
                >
                  <span className="grid size-6 place-items-center rounded-full bg-muted text-[10px] font-semibold uppercase text-foreground">
                    {user ? initialsOf(user) : "?"}
                  </span>
                  <span className="hidden max-w-[14ch] truncate sm:block">
                    {user?.full_name || user?.email || "Account"}
                  </span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                {user && (
                  <>
                    <DropdownMenuLabel>
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium text-foreground">
                          {user.full_name || "Account"}
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
                  Log out
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
      </div>
    </div>
  )
}
