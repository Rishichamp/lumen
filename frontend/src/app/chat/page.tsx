"use client";

import { Loader2, Send, Sparkles } from "lucide-react";
import { useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api, type ChatMessage } from "@/lib/api";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState<number | undefined>(undefined);
  const scrollRef = useRef<HTMLDivElement>(null);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text, citations: [] }]);
    setSending(true);

    try {
      const res = await api.chat.send(text, sessionId);
      setSessionId(res.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer, citations: res.citations }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong reaching the research assistant. Please try again.", citations: [] },
      ]);
    } finally {
      setSending(false);
      requestAnimationFrame(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }));
    }
  }

  return (
    <AppShell>
      <div className="mx-auto flex h-full max-w-3xl flex-col px-8 py-8">
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <EmptyState onPrompt={(p) => setInput(p)} />
          ) : (
            <div className="flex flex-col gap-5">
              {messages.map((m, i) => (
                <MessageBubble key={i} message={m} />
              ))}
              {sending && (
                <div className="flex items-center gap-2 text-sm text-content-muted">
                  <Loader2 className="animate-spin" size={14} /> Reading your library…
                </div>
              )}
            </div>
          )}
        </div>

        <form onSubmit={handleSend} className="mt-4 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about your papers…"
            className="input-field"
            autoFocus
          />
          <button type="submit" className="btn-primary" disabled={sending || !input.trim()}>
            <Send size={16} />
          </button>
        </form>
      </div>
    </AppShell>
  );
}

function EmptyState({ onPrompt }: { onPrompt: (p: string) => void }) {
  const suggestions = [
    "Summarize the key contribution of my most recently uploaded paper",
    "What methods have I read about for reducing hallucination in RAG?",
    "Compare the evaluation setups across my uploaded papers",
  ];
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
      <Sparkles className="text-glow" size={28} />
      <div>
        <h2 className="font-display text-2xl">Ask your library anything</h2>
        <p className="mt-1 text-sm text-content-muted">Every answer is grounded in your papers, with page-level citations.</p>
      </div>
      <div className="flex flex-col gap-2">
        {suggestions.map((s) => (
          <button key={s} onClick={() => onPrompt(s)} className="glass-panel glass-panel-hover px-4 py-2.5 text-left text-sm text-content-muted">
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
          isUser ? "bg-glow text-ink" : "glass-panel text-content-primary"
        }`}
      >
        {message.content}
      </div>
      {message.citations.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {message.citations.map((c, i) => (
            <span
              key={c.chunk_id}
              title={c.snippet}
              className="cursor-help rounded-full border border-fresh/30 bg-fresh/10 px-2 py-0.5 font-mono text-[10px] text-fresh"
            >
              [{i + 1}] {c.paper_title.slice(0, 24)}{c.paper_title.length > 24 ? "…" : ""} · p.{c.page_number}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
