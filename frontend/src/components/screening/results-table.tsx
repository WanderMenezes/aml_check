"use client";

import Link from "next/link";

import { RiskBadge } from "@/components/shared/risk-badge";
import { ScreeningRequest } from "@/lib/types";
import { useAppShell } from "@/providers/app-shell-provider";

export function ResultsTable({ screenings }: { screenings: ScreeningRequest[] }) {
  const { t } = useAppShell();

  return (
    <div className="overflow-hidden rounded-lg border border-white/10 bg-white/5">
      <table className="min-w-full divide-y divide-white/10 text-sm">
        <thead className="bg-white/5 text-left text-slate-300">
          <tr>
            <th className="px-4 py-3">{t("fullName")}</th>
            <th className="px-4 py-3">{t("source")}</th>
            <th className="px-4 py-3">{t("score")}</th>
            <th className="px-4 py-3">{t("risk")}</th>
            <th className="px-4 py-3">{t("recommendation")}</th>
            <th className="px-4 py-3">{t("details")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {screenings.map((screening) => {
            const topMatch = screening.matches[0];
            const subject = screening.client.full_name || screening.client.country;
            return (
              <tr key={screening.id} className="align-top text-slate-100">
                <td className="px-4 py-4">
                  <div className="font-medium">{subject}</div>
                  <div className="text-xs text-slate-400">{screening.client.country}</div>
                </td>
                <td className="px-4 py-4">{topMatch?.source_code || "-"}</td>
                <td className="px-4 py-4">{topMatch?.score ? `${topMatch.score}%` : "-"}</td>
                <td className="px-4 py-4">
                  <RiskBadge level={screening.risk_level} />
                </td>
                <td className="px-4 py-4 text-slate-300">{screening.recommendation}</td>
                <td className="px-4 py-4">
                  <Link href={`/screening/results?id=${screening.id}`} className="rounded-lg border border-teal/30 px-3 py-2 text-teal">
                    {t("view")}
                  </Link>
                </td>
              </tr>
            );
          })}
          {!screenings.length ? (
            <tr>
              <td className="px-4 py-6 text-center text-slate-400" colSpan={6}>
                {t("noData")}
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
