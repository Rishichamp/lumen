"use client";

import { BrainCircuit, Library, MessageSquare } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api, type PaperListItem, type ReviewCard } from "@/lib/api";

export default function DashboardPage() {
  const [papers, setPapers] = useState<PaperListItem[]>([]);
  const [dueCards, setDueCards] = useState<ReviewCard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.papers.list(), api.review.due()])
      .then(([p, cards]) => {
        setPapers(p);
        setDueCards(cards);
      })
      .finally(() => setLoading(false));
  }, []);

  const readyCount = papers.filter((p) => p.status === "ready").length;
  const processingCount = papers.filter((p) => p.status === "processing").length;

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl px-8 py-10">
        <h1 className="font-display text-3xl">Good to see you.</h1>
        <p className="mt-1 text-content-muted">Here&apos;s where your research stands today.</p>

        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard label="Papers in library" value={readyCount} sub={processingCount > 0 ? `${processingCount} processing` : undefined} />
          <StatCard label="Reviews due today" value={dueCards.length} accent={dueCards.length > 0} />
          <StatCard label="Total chunks indexed" value={papers.length > 0 ? "Ready to query" : "—"} isText />
        </div>

        <section className="mt-10">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 font-display text-xl">
              <BrainCircuit size={18} className="text-glow" />
              Today&apos;s review queue
            </h2>
            {dueCards.length > 0 && (
              <Link href="/review" className="text-sm text-glow hover:underline">
                Start review session →
              </Link>
            )}
          </div>

          <div className="glass-panel p-6">
            {loading ? (
              <p className="text-sm text-content-muted">Loading…</p>
            ) : dueCards.length === 0 ? (
              <p className="text-sm text-content-muted">
                Nothing due right now — concepts you&apos;ve retained well surface again on their own schedule.
              </p>
            ) : (
              <p className="text-sm text-content-primary">
                You have <span className="text-glow font-medium">{dueCards.length}</span> concept
                {dueCards.length === 1 ? "" : "s"} ready to review — a few minutes now keeps them from fading.
              </p>
            )}
          </div>
        </section>

        <section className="mt-10">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 font-display text-xl">
              <Library size={18} className="text-fresh" />
              Recent papers
            </h2>
            <Link href="/library" className="text-sm text-content-muted hover:text-content-primary">
              View library →
            </Link>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {papers.slice(0, 4).map((p) => (
              <div key={p.id} className="glass-panel glass-panel-hover p-4">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="line-clamp-2 text-sm font-medium">{p.title}</h3>
                  <StatusPill status={p.status} />
                </div>
              </div>
            ))}
            {papers.length === 0 && !loading && (
              <div className="glass-panel col-span-2 flex flex-col items-center gap-3 p-8 text-center">
                <p className="text-sm text-content-muted">Your library is empty. Upload your first paper to start.</p>
                <Link href="/library" className="btn-primary">
                  <MessageSquare size={16} /> Upload a paper
                </Link>
              </div>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function StatCard({
  label, value, sub, accent, isText,
}: { label: string; value: number | string; sub?: string; accent?: boolean; isText?: boolean }) {
  return (
    <div className="glass-panel p-5">
      <p className="text-xs text-content-muted">{label}</p>
      <p className={`mt-1 font-display text-3xl ${accent ? "text-glow" : ""} ${isText ? "text-xl" : ""}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-content-faint">{sub}</p>}
    </div>
  );
}

function StatusPill({ status }: { status: PaperListItem["status"] }) {
  const styles = {
    ready: "bg-fresh/10 text-fresh border-fresh/30",
    processing: "bg-glow/10 text-glow border-glow/30 animate-pulse-glow",
    failed: "bg-red-500/10 text-red-400 border-red-500/30",
  } as const;
  return (
    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}
