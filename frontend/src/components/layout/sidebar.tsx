"use client";

import clsx from "clsx";
import {
  Bell,
  FileText,
  Gauge,
  LogOut,
  PlugZap,
  ScrollText,
  SearchCheck,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Users
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAppShell } from "@/providers/app-shell-provider";

const items = [
  { href: "/dashboard", icon: Gauge, key: "dashboard" as const },
  { href: "/screening/new", icon: SearchCheck, key: "screening" as const },
  { href: "/screening/results", icon: ShieldCheck, key: "results" as const },
  { href: "/reports", icon: FileText, key: "reports" as const },
  { href: "/alerts", icon: Bell, key: "alerts" as const },
  { href: "/audit-logs", icon: ScrollText, key: "auditLogs" as const },
  { href: "/integrations", icon: PlugZap, key: "integrations" as const },
  { href: "/rules", icon: SlidersHorizontal, key: "rulesEngine" as const },
  { href: "/users", icon: Users, key: "users" as const },
  { href: "/settings", icon: Settings2, key: "settings" as const }
];

export function Sidebar() {
  const { t } = useAppShell();
  const pathname = usePathname();

  return (
    <aside className="hidden w-72 shrink-0 flex-col rounded-lg border border-white/10 bg-[#08141f]/95 p-5 shadow-glow lg:flex">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.28em] text-teal">{t("monitoring")}</p>
        <h1 className="mt-3 text-2xl font-semibold text-white">{t("appName")}</h1>
      </div>
      <nav className="space-y-2">
        {items.map(({ href, icon: Icon, key }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 rounded-lg border px-4 py-3 text-sm transition",
                active
                  ? "border-teal/50 bg-teal/10 text-white"
                  : "border-white/6 bg-white/[0.03] text-slate hover:border-teal/50 hover:bg-teal/10 hover:text-white"
              )}
            >
              <Icon size={18} />
              <span>{t(key)}</span>
            </Link>
          );
        })}
      </nav>
      <Link
        href="/logout"
        className="mt-auto flex items-center gap-3 rounded-lg border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100"
      >
        <LogOut size={18} />
        <span>{t("logout")}</span>
      </Link>
    </aside>
  );
}
