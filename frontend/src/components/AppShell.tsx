"use client";

import { BrainCircuit, LayoutDashboard, Library, MessageSquare, Sparkles } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { CommandPalette } from "@/components/CommandPalette";
import { useAuthStore } from "@/lib/auth-store";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/library", label: "Library", icon: Library },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/review", label: "Review", icon: BrainCircuit },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, isLoading, hydrate } = useAuthStore();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-content-muted">
        <Sparkles className="animate-pulse-glow" size={20} />
      </div>
    );
  }

  if (!user) return null; // redirect in-flight

  return (
    <div className="flex h-screen overflow-hidden">
      <CommandPalette />

      <aside className="flex w-60 shrink-0 flex-col border-r border-glass-border bg-ink-deep/60 p-4">
        <div className="mb-8 flex items-center gap-2 px-2">
          <Sparkles className="text-glow" size={20} />
          <span className="font-display text-lg tracking-tight">Lumen</span>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname?.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                  active
                    ? "bg-glass border border-glass-border text-content-primary"
                    : "text-content-muted hover:bg-glass hover:text-content-primary"
                }`}
              >
                <Icon size={17} />
                {label}
              </Link>
            );
          })}
        </nav>

        <button
          onClick={() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))}
          className="glass-panel glass-panel-hover flex items-center justify-between px-3 py-2 text-xs text-content-muted"
        >
          Quick search
          <span className="kbd">⌘K</span>
        </button>

        <div className="mt-4 truncate px-2 text-xs text-content-faint">{user.email}</div>
      </aside>

      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
