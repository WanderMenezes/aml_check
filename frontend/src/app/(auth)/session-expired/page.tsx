"use client";

import Link from "next/link";

import { useAppShell } from "@/providers/app-shell-provider";

export default function SessionExpiredPage() {
  const { t } = useAppShell();

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink bg-radial px-4 text-slate-100">
      <main className="w-full max-w-md rounded-lg border border-white/10 bg-white/5 p-6 text-center shadow-glow">
        <h1 className="text-2xl font-semibold text-white">{t("sessionExpired")}</h1>
        <p className="mt-3 text-sm text-slate-300">{t("sessionExpiredMessage")}</p>
        <Link href="/login" className="mt-6 inline-flex rounded-lg bg-teal px-4 py-3 font-semibold text-ink">
          {t("login")}
        </Link>
      </main>
    </div>
  );
}
