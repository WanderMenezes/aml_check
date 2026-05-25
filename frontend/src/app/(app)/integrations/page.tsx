"use client";

import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import { SanctionsSource } from "@/lib/types";
import { useAppShell } from "@/providers/app-shell-provider";

interface SyncLog {
  id: number;
  source_code: string;
  status: string;
  error_message: string;
  items_processed: number;
  started_at: string;
}

interface Summary {
  sources: SanctionsSource[];
  by_source: Array<{ source__code: string; total: number }>;
}

export default function IntegrationsPage() {
  const { t } = useAppShell();
  const [summary, setSummary] = useState<Summary>({ sources: [], by_source: [] });
  const [logs, setLogs] = useState<SyncLog[]>([]);
  const [syncing, setSyncing] = useState<number | null>(null);

  const load = () => {
    api.get("/intelligence/summary/").then(({ data }) => setSummary(data)).catch(() => setSummary({ sources: [], by_source: [] }));
    api.get("/intelligence/sync/").then(({ data }) => setLogs(data.results ?? data)).catch(() => setLogs([]));
  };

  useEffect(() => {
    load();
  }, []);

  const countBySource = new Map(summary.by_source.map((item) => [item.source__code, item.total]));

  return (
    <section className="rounded-lg border border-white/10 bg-white/5 p-5">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">{t("integrationHealth")}</p>
          <h2 className="text-xl font-semibold text-white">{t("integrations")}</h2>
        </div>
        <button type="button" onClick={load} className="rounded-lg border border-white/10 p-3 text-slate-100" title={t("refresh")}>
          <RefreshCw size={16} />
        </button>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {summary.sources.map((source) => {
          const sourceLogs = logs.filter((log) => log.source_code === source.code).slice(0, 2);
          return (
            <article key={source.id} className="rounded-lg border border-white/10 bg-ink/60 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-white">
                    {source.code} - {source.name}
                  </p>
                  <p className="mt-1 text-sm text-slate-400">{source.endpoint}</p>
                </div>
                <span className="rounded-lg border border-white/10 px-3 py-1 text-sm text-slate-200">{source.health_status}</span>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-white/10 p-3">
                  <p className="text-xs text-slate-400">{t("records")}</p>
                  <p className="text-lg font-semibold text-white">{countBySource.get(source.code) ?? 0}</p>
                </div>
                <div className="rounded-lg border border-white/10 p-3">
                  <p className="text-xs text-slate-400">{t("lastSync")}</p>
                  <p className="text-sm text-white">{source.last_synced_at ? new Date(source.last_synced_at).toLocaleString() : t("neverSynced")}</p>
                </div>
                <button
                  type="button"
                  disabled={syncing === source.id}
                  onClick={async () => {
                    setSyncing(source.id);
                    try {
                      await api.post(`/intelligence/sources/${source.id}/sync_now/`);
                      load();
                    } finally {
                      setSyncing(null);
                    }
                  }}
                  className="rounded-lg bg-teal px-3 py-2 font-semibold text-ink disabled:opacity-60"
                >
                  {syncing === source.id ? t("loading") : t("syncNow")}
                </button>
              </div>
              <div className="mt-4 space-y-2">
                {sourceLogs.map((log) => (
                  <div key={log.id} className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-300">
                    {log.status} - {log.items_processed} - {new Date(log.started_at).toLocaleString()}
                    {log.error_message ? <p className="mt-1 text-rose-300">{log.error_message}</p> : null}
                  </div>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
