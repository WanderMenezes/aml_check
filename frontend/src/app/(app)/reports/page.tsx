"use client";

import { FileDown } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import { useAppShell } from "@/providers/app-shell-provider";

interface ReportItem {
  id: number;
  language: string;
  created_at: string;
  file_url: string;
  screening: number;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export default function ReportsPage() {
  const { t } = useAppShell();
  const [reports, setReports] = useState<ReportItem[]>([]);

  useEffect(() => {
    api.get("/screening/reports/").then(({ data }) => setReports(data.results ?? data)).catch(() => setReports([]));
  }, []);

  return (
    <section className="rounded-lg border border-white/10 bg-white/5 p-5">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">{t("reportsCenter")}</p>
          <h2 className="text-xl font-semibold text-white">{t("reports")}</h2>
        </div>
      </div>
      <div className="space-y-3">
        {reports.map((report) => {
          const href = report.file_url.startsWith("http") ? report.file_url : `${BACKEND_URL}${report.file_url}`;
          return (
            <div key={report.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 bg-ink/60 p-4">
              <div>
                <p className="font-medium text-white">#{report.screening}</p>
                <p className="text-sm text-slate-400">{new Date(report.created_at).toLocaleString()}</p>
              </div>
              <a href={href} className="inline-flex items-center gap-2 rounded-lg bg-teal px-4 py-2 font-medium text-ink" target="_blank" rel="noreferrer">
                <FileDown size={16} />
                {t("download")}
              </a>
            </div>
          );
        })}
        {!reports.length ? <p className="text-sm text-slate-400">{t("noData")}</p> : null}
      </div>
    </section>
  );
}
