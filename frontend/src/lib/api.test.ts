import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, formatDetail } from "@/lib/api";

function jsonResponse(status: number, body: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const store = new Map<string, string>();
beforeEach(() => {
  store.clear();
  vi.stubGlobal("window", {
    localStorage: {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => store.set(k, v),
      removeItem: (k: string) => store.delete(k),
    },
  });
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("formatDetail", () => {
  it("passes plain strings through", () => {
    expect(formatDetail("Incorrect email or password")).toBe("Incorrect email or password");
  });

  it("joins FastAPI validation errors instead of showing [object Object]", () => {
    const detail = [
      { loc: ["body", "email"], msg: "value is not a valid email address", type: "value_error" },
      { loc: ["body", "password"], msg: "String should have at least 8 characters", type: "string_too_short" },
    ];
    expect(formatDetail(detail)).toBe(
      "value is not a valid email address; String should have at least 8 characters",
    );
  });

  it("returns undefined for anything else", () => {
    expect(formatDetail(undefined)).toBeUndefined();
    expect(formatDetail({ weird: true })).toBeUndefined();
  });
});

describe("request", () => {
  it("sends the stored token and parses JSON", async () => {
    store.set("lumen_token", "abc");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, [{ id: 1 }]));
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.papers.list()).resolves.toEqual([{ id: 1 }]);
    const init = fetchMock.mock.calls[0]![1] as RequestInit;
    expect((init.headers as Headers).get("Authorization")).toBe("Bearer abc");
    expect((init.headers as Headers).get("Content-Type")).toBe("application/json");
  });

  it("does not force a JSON content type on uploads", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, { id: 2 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.papers.upload(new File(["%PDF-1.4"], "a.pdf", { type: "application/pdf" }));
    const init = fetchMock.mock.calls[0]![1] as RequestInit;
    expect((init.headers as Headers).has("Content-Type")).toBe(false);
  });

  it("turns error responses into ApiError with a readable message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      jsonResponse(422, { detail: [{ loc: ["body", "email"], msg: "bad email" }] }),
    ));
    const err = await api.auth.login("x", "y").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.message).toBe("bad email");
  });

  it("returns undefined for 204 No Content", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    await expect(api.papers.remove(3)).resolves.toBeUndefined();
  });
});
