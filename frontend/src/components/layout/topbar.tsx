"use client";

import { Bell, Globe, LogOut, MoonStar, SunMedium } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

import { api } from "@/lib/api/client";
import { Locale, TranslationKey } from "@/lib/i18n/translations";
import { useAppShell } from "@/providers/app-shell-provider";

const titleByPath: Array<[string, TranslationKey]> = [
  ["/screening/new", "newScreening"],
  ["/screening/results", "results"],
  ["/reports", "reports"],
  ["/alerts", "alerts"],
  ["/audit-logs", "auditLogs"],
  ["/integrations", "integrations"],
  ["/rules", "rulesEngine"],
  ["/users", "usersManagement"],
  ["/settings", "settings"],
  ["/dashboard", "dashboard"]
];

export function Topbar() {
  const router = useRouter();
  const pathname = usePathname();
  const { locale, setLocale, theme, setTheme, t, user, setAuth } = useAppShell();
  const titleKey = titleByPath.find(([path]) => pathname.startsWith(path))?.[1] ?? "dashboard";

  const logout = async () => {
    try {
      await api.post("/auth/logout/");
    } finally {
      setAuth(null);
      router.push("/login");
    }
  };

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-white/10 bg-white/5 px-5 py-4 backdrop-blur">
      <div>
        <p className="text-xs uppercase tracking-[0.28em] text-teal">{t("complianceOps")}</p>
        <h2 className="text-xl font-semibold text-white">{t(titleKey)}</h2>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100">
          <Globe size={16} />
          {(["pt", "en"] as Locale[]).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setLocale(item)}
              className={`rounded-md px-2 py-1 ${locale === item ? "bg-teal text-ink" : "text-slate-300"}`}
            >
              {item.toUpperCase()}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="rounded-lg border border-white/10 bg-white/5 p-3 text-slate-100"
          title={t("theme")}
        >
          {theme === "dark" ? <SunMedium size={16} /> : <MoonStar size={16} />}
        </button>
        <button type="button" className="rounded-lg border border-white/10 bg-white/5 p-3 text-slate-100" title={t("alerts")}>
          <Bell size={16} />
        </button>
        <div className="hidden rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-100 md:block">
          {(user?.email as string) || ""}
        </div>
        <button
          type="button"
          onClick={logout}
          className="rounded-lg border border-rose-400/20 bg-rose-500/10 p-3 text-rose-200"
          title={t("logout")}
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
}
