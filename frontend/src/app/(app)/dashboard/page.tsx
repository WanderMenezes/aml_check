"use client";

import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Clock3, Globe2 } from "lucide-react";

import { StatCard } from "@/components/dashboard/stat-card";
import { TrendChart } from "@/components/dashboard/trend-chart";
import { RiskBadge } from "@/components/shared/risk-badge";
import { api } from "@/lib/api/client";
import { ScreeningRequest } from "@/lib/types";
import { useAppShell } from "@/providers/app-shell-provider";

interface DashboardPayload {
  totals: {
    screenings: number;
    critical: number;
    pending: number;
    review: number;
    high_risk_countries: number;
    avg_score?: number;
    unread_alerts?: number;
  };
  risk_distribution: { risk_level: string; total: number }[];
  timeseries?: { date: string; total: number }[];
  top_sources?: { source_code: string; total: number }[];
  recent_screenings: ScreeningRequest[];
  recent_alerts: { id: number; title: string; message: string; is_read: boolean }[];
}

export default function DashboardPage() {
  const { t } = useAppShell();
  const [data, setData] = useState<DashboardPayload | null>(null);

  useEffect(() => {
    api.get("/screening/dashboard/").then(({ data }) => setData(data)).catch(() => setData(null));
  }, []);

  const chartValues = data?.risk_distribution.map((item) => item.total) ?? [];
  const timeseriesValues = data?.timeseries?.map((d) => d.total) ?? [];

  return (
    <div className="space-y-5">
      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-6">
        <StatCard eyebrow={t("totalScreenings")} value={data?.totals.screenings ?? 0} accent="bg-teal/10 text-teal" icon={<Activity size={20} />} />
        <StatCard eyebrow={t("criticalScreenings")} value={data?.totals.critical ?? 0} accent="bg-rose-500/10 text-rose-200" icon={<AlertTriangle size={20} />} />
        <StatCard eyebrow={t("pendingScreenings")} value={data?.totals.pending ?? 0} accent="bg-amber-500/10 text-amber-200" icon={<Clock3 size={20} />} />
        <StatCard eyebrow={t("highRiskCountries")} value={data?.totals.high_risk_countries ?? 0} accent="bg-sky-500/10 text-sky-200" icon={<Globe2 size={20} />} />
        <StatCard eyebrow={t("avgMatchScore")} value={data?.totals.avg_score ?? 0} accent="bg-indigo-500/10 text-indigo-200" icon={<Activity size={20} />} />
        <StatCard eyebrow={t("unreadAlerts")} value={data?.totals.unread_alerts ?? 0} accent="bg-fuchsia-500/10 text-fuchsia-200" icon={<AlertTriangle size={20} />} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <TrendChart values={timeseriesValues.length ? timeseriesValues : chartValues} />
        <div className="rounded-lg border border-white/10 bg-white/5 p-5">
          <div className="mb-5 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">{t("alerts")}</h3>
            <span className="text-xs uppercase tracking-[0.24em] text-teal">{t("alertsUnread")}</span>
          </div>
          <div className="space-y-3">
            {(data?.recent_alerts ?? []).map((alert) => (
              <div key={alert.id} className="rounded-lg border border-white/10 bg-ink/60 p-4">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-white">{alert.title}</p>
                  <RiskBadge level={alert.is_read ? "LOW" : "MEDIUM"} />
                </div>
                <p className="mt-2 text-sm text-slate-300">{alert.message}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_0.8fr]">
        <div className="rounded-lg border border-white/10 bg-white/5 p-5">
          <h3 className="mb-4 text-lg font-semibold text-white">Top fontes (últimos 30 dias)</h3>
          <div className="space-y-2">
            {(data?.top_sources ?? []).map((s) => (
              <div key={s.source_code} className="flex items-center justify-between rounded-md bg-ink/60 p-3">
                <div className="text-sm text-slate-300">{s.source_code}</div>
                <div className="font-semibold text-white">{s.total}</div>
              </div>
            ))}
            {!data?.top_sources?.length ? <p className="text-sm text-slate-400">Nenhuma fonte encontrada.</p> : null}
          </div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/5 p-5">
          <h3 className="mb-4 text-lg font-semibold text-white">Atividade diária</h3>
          <TrendChart values={timeseriesValues} />
        </div>
      </section>

      <section className="rounded-lg border border-white/10 bg-white/5 p-5">
        <h3 className="mb-4 text-lg font-semibold text-white">{t("screeningHistory")}</h3>
        <div className="space-y-3">
          {(data?.recent_screenings ?? []).map((screening) => (
            <div key={screening.id} className="rounded-lg border border-white/10 bg-ink/60 px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium text-white">{screening.client.full_name}</p>
                  <p className="text-sm text-slate-400">{screening.client.country}</p>
                </div>
                <div className="flex items-center gap-3">
                  <RiskBadge level={screening.risk_level} />
                  <p className="text-sm text-slate-300">{screening.recommendation}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
