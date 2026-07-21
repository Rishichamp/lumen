/**
 * Thin typed fetch wrapper around the FastAPI backend.
 *
 * Kept deliberately dependency-free (no axios/react-query here) so the
 * whole client surface is auditable in one file. Token is read from
 * localStorage per-call rather than held in a module-level variable so
 * server components / multiple tabs never see a stale in-memory copy.
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("lumen_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* response had no JSON body */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------- Types (mirror backend Pydantic schemas) ----------
export interface User {
  id: number;
  email: string;
  full_name: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface PaperListItem {
  id: number;
  title: string;
  authors: string;
  status: "processing" | "ready" | "failed";
  created_at: string;
  tags: string[];
}

export interface PaperDetail extends PaperListItem {
  abstract: string;
  arxiv_id: string | null;
  page_count: number;
  summary: string;
}

export interface Citation {
  paper_id: number;
  paper_title: string;
  chunk_id: number;
  page_number: number;
  snippet: string;
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at?: string;
}

export interface ChatResponse {
  session_id: number;
  answer: string;
  citations: Citation[];
}

export interface SearchResult {
  paper_id: number;
  paper_title: string;
  chunk_id: number;
  page_number: number;
  snippet: string;
  score: number;
}

export interface ReviewCard {
  id: number;
  concept_id: number;
  question: string;
  answer: string;
  interval_days: number;
  repetitions: number;
  next_review_at: string;
}

// ---------- API surface ----------
export const api = {
  auth: {
    register: (email: string, password: string, full_name: string) =>
      request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify({ email, password, full_name }) }),
    login: (email: string, password: string) =>
      request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
    me: () => request<User>("/auth/me"),
  },
  papers: {
    list: () => request<PaperListItem[]>("/papers"),
    get: (id: number) => request<PaperDetail>(`/papers/${id}`),
    upload: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return request<PaperDetail>("/papers", { method: "POST", body: form });
    },
    remove: (id: number) => request<void>(`/papers/${id}`, { method: "DELETE" }),
  },
  chat: {
    sessions: () => request<{ id: number; title: string; scope_paper_id: number | null; created_at: string }[]>("/chat/sessions"),
    messages: (sessionId: number) => request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`),
    send: (message: string, sessionId?: number, scopePaperId?: number) =>
      request<ChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify({ message, session_id: sessionId ?? null, scope_paper_id: scopePaperId ?? null }),
      }),
  },
  search: {
    query: (q: string, limit = 10) => request<SearchResult[]>(`/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  },
  review: {
    due: () => request<ReviewCard[]>("/review/due"),
    grade: (cardId: number, quality: number) =>
      request<ReviewCard>(`/review/${cardId}/grade`, { method: "POST", body: JSON.stringify({ quality }) }),
  },
};

export function setToken(token: string) {
  window.localStorage.setItem("lumen_token", token);
}

export function clearToken() {
  window.localStorage.removeItem("lumen_token");
}
