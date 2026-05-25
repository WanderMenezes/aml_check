"use client";

import { LockKeyhole, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api/client";
import { useAppShell } from "@/providers/app-shell-provider";

export default function LoginPage() {
  const router = useRouter();
  const { t, setAuth } = useAppShell();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  return (
    <div className="min-h-screen bg-ink bg-radial px-4 py-8 text-slate-100">
      <main className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1fr_420px]">
        <section className="space-y-6">
          <div className="inline-flex items-center gap-3 rounded-lg border border-teal/30 bg-teal/10 px-4 py-3 text-teal">
            <ShieldCheck size={20} />
            <span className="text-sm font-semibold">{t("appName")}</span>
          </div>
          <div>
            <h1 className="max-w-2xl text-4xl font-semibold text-white lg:text-5xl">{t("signIn")}</h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-slate-300">{t("welcome")}</p>
          </div>
          <div className="grid max-w-2xl gap-3 sm:grid-cols-3">
            {[t("security"), t("continuousMonitoring"), t("auditLogs")].map((item) => (
              <div key={item} className="rounded-lg border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/5 p-6 shadow-glow backdrop-blur">
          <div className="mb-6 flex items-center gap-3">
            <div className="rounded-lg bg-teal/15 p-3 text-teal">
              <LockKeyhole />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">{t("login")}</h2>
              <p className="text-sm text-slate-300">{t("security")}</p>
            </div>
          </div>
          <form
            className="space-y-4"
            onSubmit={async (event) => {
              event.preventDefault();
              setLoading(true);
              setError("");
              try {
                const { data } = await api.post("/auth/login/", { email, password });
                setAuth(data);
                router.push("/dashboard");
              } catch {
                setError(t("authenticationFailed"));
              } finally {
                setLoading(false);
              }
            }}
          >
            <label className="space-y-2">
              <span className="text-sm text-slate-300">{t("email")}</span>
              <input
                type="email"
                autoComplete="email"
                className="w-full rounded-lg border border-white/10 bg-ink/70 px-4 py-3 text-white outline-none transition focus:border-teal/60"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-slate-300">{t("password")}</span>
              <input
                type="password"
                autoComplete="current-password"
                className="w-full rounded-lg border border-white/10 bg-ink/70 px-4 py-3 text-white outline-none transition focus:border-teal/60"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            {error ? <p className="text-sm text-rose-300">{error}</p> : null}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-teal px-4 py-3 font-semibold text-ink transition hover:brightness-110 disabled:opacity-60"
            >
              {loading ? t("loading") : t("login")}
            </button>
            <Link href="/forgot-password" className="block text-center text-sm text-teal">
              {t("forgotPassword")}
            </Link>
          </form>
        </section>
      </main>
    </div>
  );
}
