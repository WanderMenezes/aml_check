"use client";

import { useAppShell } from "@/providers/app-shell-provider";

export default function SettingsPage() {
  const { locale, setLocale, theme, setTheme, t } = useAppShell();

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <section className="rounded-lg border border-white/10 bg-white/5 p-5">
        <h2 className="mb-5 text-xl font-semibold text-white">{t("settings")}</h2>
        <div className="space-y-4">
          <label className="block space-y-2">
            <span className="text-sm text-slate-300">{t("language")}</span>
            <select
              className="w-full rounded-lg border border-white/10 bg-ink px-3 py-3 text-white"
              value={locale}
              onChange={(event) => setLocale(event.target.value as "pt" | "en")}
            >
              <option value="pt">Português</option>
              <option value="en">English</option>
            </select>
          </label>
          <label className="block space-y-2">
            <span className="text-sm text-slate-300">{t("theme")}</span>
            <select
              className="w-full rounded-lg border border-white/10 bg-ink px-3 py-3 text-white"
              value={theme}
              onChange={(event) => setTheme(event.target.value as "light" | "dark")}
            >
              <option value="dark">{t("dark")}</option>
              <option value="light">{t("light")}</option>
            </select>
          </label>
          <label className="block space-y-2">
            <span className="text-sm text-slate-300">{t("timezone")}</span>
            <input className="w-full rounded-lg border border-white/10 bg-ink px-3 py-3 text-white" value="Africa/Sao_Tome" readOnly />
          </label>
        </div>
      </section>
      <section className="rounded-lg border border-white/10 bg-white/5 p-5">
        <h2 className="mb-5 text-xl font-semibold text-white">{t("security")}</h2>
        <div className="grid gap-3">
          {[t("apis"), t("branding"), t("continuousMonitoring")].map((item) => (
            <div key={item} className="rounded-lg border border-white/10 bg-ink/60 p-4">
              <p className="font-medium text-white">{item}</p>
              <p className="mt-1 text-sm text-slate-400">{t("enabled")}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
