"use client";

import { BrainCircuit, CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api, type ReviewCard } from "@/lib/api";

const GRADE_OPTIONS = [
  { quality: 1, label: "Forgot", hint: "1d", className: "border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20" },
  { quality: 3, label: "Hard", hint: "~6d", className: "border-glow/30 bg-glow/10 text-glow hover:bg-glow/20" },
  { quality: 5, label: "Easy", hint: "grows", className: "border-fresh/30 bg-fresh/10 text-fresh hover:bg-fresh/20" },
] as const;

export default function ReviewPage() {
  const [queue, setQueue] = useState<ReviewCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [revealed, setRevealed] = useState(false);
  const [reviewedCount, setReviewedCount] = useState(0);

  useEffect(() => {
    api.review.due().then(setQueue).finally(() => setLoading(false));
  }, []);

  async function grade(quality: number) {
    const current = queue[0];
    if (!current) return;
    await api.review.grade(current.id, quality);
    setQueue((prev) => prev.slice(1));
    setReviewedCount((c) => c + 1);
    setRevealed(false);
  }

  const current = queue[0];

  return (
    <AppShell>
      <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center px-8 py-10">
        {loading ? (
          <p className="text-sm text-content-muted">Loading your review queue…</p>
        ) : !current ? (
          <div className="flex flex-col items-center gap-3 text-center">
            <CheckCircle2 className="text-fresh" size={32} />
            <h1 className="font-display text-2xl">
              {reviewedCount > 0 ? "Queue cleared." : "Nothing due right now."}
            </h1>
            <p className="max-w-sm text-sm text-content-muted">
              {reviewedCount > 0
                ? `You reviewed ${reviewedCount} concept${reviewedCount === 1 ? "" : "s"}. Come back when the next batch is due.`
                : "As you upload and chat with papers, key concepts get scheduled here for spaced review."}
            </p>
          </div>
        ) : (
          <div className="w-full animate-fade-up">
            <div className="mb-4 flex items-center justify-between text-xs text-content-muted">
              <span className="flex items-center gap-1.5">
                <BrainCircuit size={14} className="text-glow" /> {queue.length} remaining
              </span>
              <span>{current.repetitions === 0 ? "New concept" : `Reviewed ${current.repetitions}×`}</span>
            </div>

            <div
              onClick={() => setRevealed(true)}
              className={`glass-panel flex min-h-[220px] flex-col items-center justify-center gap-4 p-8 text-center ${
                !revealed ? "cursor-pointer" : ""
              }`}
            >
              <p className="font-display text-xl">{current.question}</p>
              {revealed && (
                <p className="border-t border-glass-border pt-4 text-sm text-content-muted">{current.answer}</p>
              )}
              {!revealed && <p className="text-xs text-content-faint">Click to reveal answer</p>}
            </div>

            {revealed && (
              <div className="mt-4 grid grid-cols-3 gap-3">
                {GRADE_OPTIONS.map((opt) => (
                  <button
                    key={opt.quality}
                    onClick={() => grade(opt.quality)}
                    className={`rounded-xl border px-3 py-3 text-sm font-medium transition-colors ${opt.className}`}
                  >
                    {opt.label}
                    <div className="mt-0.5 font-mono text-[10px] opacity-70">{opt.hint}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
