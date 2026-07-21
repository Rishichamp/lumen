"use client";

import { Command } from "cmdk";
import { FileSearch, MessageSquarePlus, LayoutDashboard, Library, BrainCircuit, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/auth-store";

/**
 * Global command palette (Cmd/Ctrl+K), modeled on Raycast/Linear's
 * pattern: a single fuzzy-searchable entry point for navigation and
 * actions, so power users never need the mouse for routine moves
 * between chat, library, and review.
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  function go(path: string) {
    setOpen(false);
    router.push(path);
  }

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Command palette"
      className="fixed left-1/2 top-[18%] z-50 w-full max-w-lg -translate-x-1/2 overflow-hidden
        rounded-2xl border border-glass-border bg-ink-soft/95 shadow-glass backdrop-blur-xl
        animate-fade-up"
    >
      <div className="flex items-center border-b border-glass-border px-4">
        <Command.Input
          placeholder="Jump to, search, or run a command…"
          className="w-full bg-transparent py-3.5 text-sm text-content-primary placeholder:text-content-faint outline-none"
        />
        <span className="kbd">esc</span>
      </div>
      <Command.List className="max-h-80 overflow-y-auto p-2">
        <Command.Empty className="px-3 py-6 text-center text-sm text-content-muted">
          No matching commands.
        </Command.Empty>

        <Command.Group heading="Navigate" className="px-2 py-1.5 text-xs font-medium text-content-faint">
          <PaletteItem icon={<LayoutDashboard size={16} />} label="Dashboard" onSelect={() => go("/dashboard")} />
          <PaletteItem icon={<Library size={16} />} label="Library" onSelect={() => go("/library")} />
          <PaletteItem icon={<MessageSquarePlus size={16} />} label="New chat" onSelect={() => go("/chat")} />
          <PaletteItem icon={<BrainCircuit size={16} />} label="Review queue" onSelect={() => go("/review")} />
        </Command.Group>

        <Command.Group heading="Search" className="px-2 py-1.5 text-xs font-medium text-content-faint">
          <PaletteItem
            icon={<FileSearch size={16} />}
            label="Semantic search your library"
            onSelect={() => go("/library?focus=search")}
          />
        </Command.Group>

        <Command.Group heading="Account" className="px-2 py-1.5 text-xs font-medium text-content-faint">
          <PaletteItem icon={<LogOut size={16} />} label="Sign out" onSelect={() => { logout(); go("/login"); }} />
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}

function PaletteItem({ icon, label, onSelect }: { icon: React.ReactNode; label: string; onSelect: () => void }) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-content-primary
        aria-selected:bg-glass-hover"
    >
      <span className="text-content-muted">{icon}</span>
      {label}
    </Command.Item>
  );
}
