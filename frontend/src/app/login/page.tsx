"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuthStore } from "@/lib/auth-store";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login, register, error } = useAuthStore();
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, fullName);
      }
      router.push("/dashboard");
    } catch {
      // error surfaced via store
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm animate-fade-up">
        <div className="mb-8 flex flex-col items-center gap-2 text-center">
          <Sparkles className="text-glow" size={28} />
          <h1 className="font-display text-2xl">Lumen</h1>
          <p className="text-sm text-content-muted">
            The research retention copilot — chat with your papers, and never forget what you read.
          </p>
        </div>

        <div className="glass-panel p-6">
          <div className="mb-6 flex rounded-xl border border-glass-border p-1 text-sm">
            <button
              className={`flex-1 rounded-lg py-1.5 transition-colors ${mode === "login" ? "bg-glass text-content-primary" : "text-content-muted"}`}
              onClick={() => setMode("login")}
              type="button"
            >
              Sign in
            </button>
            <button
              className={`flex-1 rounded-lg py-1.5 transition-colors ${mode === "register" ? "bg-glass text-content-primary" : "text-content-muted"}`}
              onClick={() => setMode("register")}
              type="button"
            >
              Create account
            </button>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            {mode === "register" && (
              <input
                required
                placeholder="Full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="input-field"
              />
            )}
            <input
              required
              type="email"
              placeholder="you@university.edu"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field"
            />
            <input
              required
              type="password"
              minLength={8}
              placeholder="Password (min. 8 characters)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
            />

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button type="submit" disabled={submitting} className="btn-primary mt-2">
              {submitting && <Loader2 className="animate-spin" size={16} />}
              {mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
