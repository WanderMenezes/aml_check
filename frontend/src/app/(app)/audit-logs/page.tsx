"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import { AuditEvent } from "@/lib/types";
import { useAppShell } from "@/providers/app-shell-provider";

export default function AuditLogsPage() {
  const { t } = useAppShell();
  const [events, setEvents] = useState<AuditEvent[]>([]);

  useEffect(() => {
    api.get("/audit/").then(({ data }) => setEvents(data.results ?? data)).catch(() => setEvents([]));
  }, []);

  return (
    <section className="rounded-lg border border-white/10 bg-white/5 p-5">
      <div className="mb-5">
        <p className="text-sm text-slate-300">{t("latestLogs")}</p>
        <h2 className="text-xl font-semibold text-white">{t("auditLogs")}</h2>
      </div>
      <div className="overflow-hidden rounded-lg border border-white/10">
        <table className="min-w-full divide-y divide-white/10 text-sm">
          <thead className="bg-white/5 text-left text-slate-300">
            <tr>
              <th className="px-4 py-3">{t("user")}</th>
              <th className="px-4 py-3">{t("action")}</th>
              <th className="px-4 py-3">{t("ipAddress")}</th>
              <th className="px-4 py-3">{t("result")}</th>
              <th className="px-4 py-3">{t("createdAt")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {events.map((event) => (
              <tr key={event.id} className="text-slate-100">
                <td className="px-4 py-4">{event.user_email || "system"}</td>
                <td className="px-4 py-4">
                  <div>{event.action}</div>
                  <div className="text-xs text-slate-400">
                    {event.resource_type}:{event.resource_id}
                  </div>
                </td>
                <td className="px-4 py-4">{event.ip_address || "-"}</td>
                <td className="px-4 py-4">{event.status}</td>
                <td className="px-4 py-4 text-slate-300">{new Date(event.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
