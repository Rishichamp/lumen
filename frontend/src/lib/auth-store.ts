"use client";

import { create } from "zustand";
import { api, ApiError, clearToken, setToken, type User } from "@/lib/api";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  error: null,

  login: async (email, password) => {
    set({ error: null });
    try {
      const res = await api.auth.login(email, password);
      setToken(res.access_token);
      set({ user: res.user });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Login failed" });
      throw e;
    }
  },

  register: async (email, password, fullName) => {
    set({ error: null });
    try {
      const res = await api.auth.register(email, password, fullName);
      setToken(res.access_token);
      set({ user: res.user });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Registration failed" });
      throw e;
    }
  },

  logout: () => {
    clearToken();
    set({ user: null });
  },

  hydrate: async () => {
    if (typeof window === "undefined" || !window.localStorage.getItem("lumen_token")) {
      set({ isLoading: false });
      return;
    }
    try {
      const user = await api.auth.me();
      set({ user, isLoading: false });
    } catch (e) {
      // Only a rejected token means "signed out"; a network error or a
      // server restart shouldn't throw the user's session away.
      if (e instanceof ApiError && e.status === 401) clearToken();
      set({ user: null, isLoading: false });
    }
  },
}));
