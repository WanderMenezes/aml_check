"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { api } from "@/lib/api/client";
import { useAppShell } from "@/providers/app-shell-provider";

export default function LogoutPage() {
  const router = useRouter();
  const { t, setAuth } = useAppShell();

  useEffect(() => {
    const run = async () => {
      try {
        await api.post("/auth/logout/");
      } finally {
        setAuth(null);
        router.replace("/login");
      }
    };
    run();
  }, [router, setAuth]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink text-slate-100">
      <div className="rounded-lg border border-white/10 bg-white/5 p-6">{t("logout")}</div>
    </div>
  );
}
