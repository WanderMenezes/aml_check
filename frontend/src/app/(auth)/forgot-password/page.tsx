"use client";

import Link from "next/link";
import { useState } from "react";

import { api } from "@/lib/api/client";
import { useAppShell } from "@/providers/app-shell-provider";

export default function ForgotPasswordPage() {
  const { t } = useAppShell();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink bg-radial px-4 text-slate-100">
      <main className="w-full max-w-md rounded-lg border border-white/10 bg-white/5 p-6 shadow-glow">
        <h1 className="text-2xl font-semibold text-white">{t("forgotPassword")}</h1>
        <form
          className="mt-6 space-y-4"
          onSubmit={async (event) => {
            event.preventDefault();
            setLoading(true);
            try {
              await api.post("/auth/password-reset/", { email });
              setMessage(t("resetSent"));
            } finally {
              setLoading(false);
            }
          }}
        >
          <label className="space-y-2">
            <span className="text-sm text-slate-300">{t("email")}</span>
            <input
              type="email"
              className="w-full rounded-lg border border-white/10 bg-ink/70 px-4 py-3 text-white outline-none transition focus:border-teal/60"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          {message ? <p className="text-sm text-teal">{message}</p> : null}
          <button className="w-full rounded-lg bg-teal px-4 py-3 font-semibold text-ink" disabled={loading} type="submit">
            {loading ? t("loading") : t("sendReset")}
          </button>
          <Link href="/login" className="block text-center text-sm text-teal">
            {t("backToLogin")}
          </Link>
        </form>
      </main>
    </div>
  );
}
