"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";

export default function RootPage() {
  const router = useRouter();
  const { user, isLoading, hydrate } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!isLoading) router.replace(user ? "/dashboard" : "/login");
  }, [isLoading, user, router]);

  return null;
}
