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

function resolveReportUrl(fileUrl: string) {
  return fileUrl.startsWith("http") ? fileUrl : `${BACKEND_URL}${fileUrl}`;
}

export default function ReportsPage() {
  const { locale, t } = useAppShell();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [exportingId, setExportingId] = useState<number | null>(null);

  useEffect(() => {
    api.get("/screening/reports/").then(({ data }) => setReports(data.results ?? data)).catch(() => setReports([]));
  }, []);

  const openReport = (href: string) => {
    const link = document.createElement("a");
    link.href = href;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.click();
  };

  const handleDownload = async (report: ReportItem) => {
    setExportingId(report.id);
    try {
      const { data } = await api.post<ReportItem>(`/screening/requests/${report.screening}/export_pdf/`, { language: locale });
      setReports((current) => current.map((item) => (item.id === data.id ? { ...item, ...data } : item)));
      openReport(resolveReportUrl(data.file_url || report.file_url));
    } finally {
      setExportingId(null);
    }
  };

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
          return (
            <div key={report.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 bg-ink/60 p-4">
              <div>
                <p className="font-medium text-white">#{report.screening}</p>
                <p className="text-sm text-slate-400">{new Date(report.created_at).toLocaleString()}</p>
              </div>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-lg bg-teal px-4 py-2 font-medium text-ink disabled:cursor-wait disabled:opacity-70"
                disabled={exportingId === report.id}
                onClick={() => handleDownload(report)}
              >
                <FileDown size={16} />
                {exportingId === report.id ? "..." : t("download")}
              </button>
            </div>
          );
        })}
        {!reports.length ? <p className="text-sm text-slate-400">{t("noData")}</p> : null}
      </div>
    </section>
  );
}
