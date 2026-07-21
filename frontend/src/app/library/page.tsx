"use client";

import { FileSearch, Loader2, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api, ApiError, type PaperListItem, type SearchResult } from "@/lib/api";

export default function LibraryPage() {
  const [papers, setPapers] = useState<PaperListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refreshPapers = useCallback(() => {
    api.papers.list().then(setPapers).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refreshPapers();
  }, [refreshPapers]);

  // Poll while any paper is still processing, so status pills update
  // without the user needing to refresh the page manually.
  useEffect(() => {
    if (!papers.some((p) => p.status === "processing")) return;
    const interval = setInterval(refreshPapers, 3000);
    return () => clearInterval(interval);
  }, [papers, refreshPapers]);

  async function handleUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      await api.papers.upload(file);
      refreshPapers();
    } catch (e) {
      setUploadError(e instanceof ApiError ? e.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) {
      setResults(null);
      return;
    }
    setSearching(true);
    try {
      setResults(await api.search.query(query));
    } finally {
      setSearching(false);
    }
  }

  async function handleDelete(id: number) {
    setPapers((prev) => prev.filter((p) => p.id !== id)); // optimistic
    try {
      await api.papers.remove(id);
    } catch {
      refreshPapers(); // revert on failure
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl px-8 py-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-3xl">Library</h1>
            <p className="mt-1 text-content-muted">Upload papers to embed and index them for chat and search.</p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
          />
          <button className="btn-primary" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? <Loader2 className="animate-spin" size={16} /> : <Upload size={16} />}
            {uploading ? "Uploading…" : "Upload paper"}
          </button>
        </div>

        {uploadError && <p className="mt-3 text-sm text-red-400">{uploadError}</p>}

        <form onSubmit={handleSearch} className="mt-6 flex gap-2">
          <div className="relative flex-1">
            <FileSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-content-faint" size={16} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Semantic search across your library…"
              className="input-field pl-9"
            />
          </div>
          <button type="submit" className="btn-secondary" disabled={searching}>
            {searching ? <Loader2 className="animate-spin" size={16} /> : "Search"}
          </button>
        </form>

        {results && (
          <div className="mt-4 flex flex-col gap-2">
            {results.length === 0 ? (
              <p className="text-sm text-content-muted">No matches found.</p>
            ) : (
              results.map((r) => (
                <div key={r.chunk_id} className="glass-panel p-4">
                  <div className="flex items-center justify-between text-xs text-content-muted">
                    <span className="font-medium text-content-primary">{r.paper_title}</span>
                    <span className="font-mono">p.{r.page_number} · {(r.score * 100).toFixed(0)}% match</span>
                  </div>
                  <p className="mt-1.5 text-sm text-content-muted">{r.snippet}</p>
                </div>
              ))
            )}
          </div>
        )}

        <div className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {loading ? (
            <p className="text-sm text-content-muted">Loading your library…</p>
          ) : papers.length === 0 ? (
            <p className="text-sm text-content-muted">No papers yet — upload your first PDF above.</p>
          ) : (
            papers.map((p) => <PaperCard key={p.id} paper={p} onDelete={() => handleDelete(p.id)} />)
          )}
        </div>
      </div>
    </AppShell>
  );
}

function PaperCard({ paper, onDelete }: { paper: PaperListItem; onDelete: () => void }) {
  return (
    <div className="glass-panel glass-panel-hover group relative p-4">
      <button
        onClick={onDelete}
        aria-label={`Delete ${paper.title}`}
        className="absolute right-3 top-3 text-content-faint opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
      >
        <Trash2 size={15} />
      </button>
      <h3 className="line-clamp-2 pr-6 text-sm font-medium">{paper.title}</h3>
      <p className="mt-1 text-xs text-content-faint">
        {new Date(paper.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {paper.tags.map((tag) => (
          <span key={tag} className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-content-muted">
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}
