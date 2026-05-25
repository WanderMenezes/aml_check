"use client";

import { AlertTriangle, CheckCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import { AlertItem } from "@/lib/types";
import { useAppShell } from "@/providers/app-shell-provider";

export default function AlertsPage() {
  const { t } = useAppShell();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  const load = () => {
    api.get("/screening/alerts/").then(({ data }) => setAlerts(data.results ?? data)).catch(() => setAlerts([]));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-5">
      <section className="grid gap-5 md:grid-cols-3">
        <div className="rounded-lg border border-white/10 bg-white/5 p-5">
          <AlertTriangle className="mb-3 text-rose-300" />
          <p className="text-sm text-slate-300">{t("criticalMatches")}</p>
          <p className="mt-2 text-3xl font-semibold text-white">{alerts.filter((item) => item.alert_type === "NEW_MATCH").length}</p>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/5 p-5">
          <AlertTriangle className="mb-3 text-amber-300" />
          <p className="text-sm text-slate-300">{t("pendingReview")}</p>
          <p className="mt-2 text-3xl font-semibold text-white">{alerts.filter((item) => item.alert_type === "PENDING_REVIEW").length}</p>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/5 p-5">
          <CheckCheck className="mb-3 text-teal" />
          <p className="text-sm text-slate-300">{t("alertsUnread")}</p>
          <p className="mt-2 text-3xl font-semibold text-white">{alerts.filter((item) => !item.is_read).length}</p>
        </div>
      </section>
      <section className="rounded-lg border border-white/10 bg-white/5 p-5">
        <h2 className="mb-5 text-xl font-semibold text-white">{t("alerts")}</h2>
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div key={alert.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 bg-ink/60 p-4">
              <div>
                <p className="font-medium text-white">{alert.title}</p>
                <p className="mt-1 text-sm text-slate-300">{alert.message}</p>
                <p className="mt-2 text-xs text-slate-500">{new Date(alert.created_at).toLocaleString()}</p>
              </div>
              {!alert.is_read ? (
                <button
                  type="button"
                  onClick={async () => {
                    await api.post(`/screening/alerts/${alert.id}/mark_read/`);
                    load();
                  }}
                  className="rounded-lg border border-teal/30 px-3 py-2 text-sm text-teal"
                >
                  {t("markRead")}
                </button>
              ) : null}
            </div>
          ))}
          {!alerts.length ? <p className="text-sm text-slate-400">{t("noData")}</p> : null}
        </div>
      </section>
    </div>
  );
}
