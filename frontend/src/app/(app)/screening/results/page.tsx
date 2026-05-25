"use client";

import React, { useDeferredValue, useEffect, useMemo, useState } from "react";

import { RiskBadge } from "@/components/shared/risk-badge";
import { ResultsTable } from "@/components/screening/results-table";
import { useDebounce } from "@/hooks/use-debounce";
import { api } from "@/lib/api/client";
import { ScreeningRequest } from "@/lib/types";
import { useAppShell } from "@/providers/app-shell-provider";

export default function ScreeningResultsPage() {
  const { t } = useAppShell();
  const [screenings, setScreenings] = useState<ScreeningRequest[]>([]);
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState(0);
  const debounced = useDebounce(search);
  const deferredSearch = useDeferredValue(debounced);

  useEffect(() => {
    api.get("/screening/requests/").then(({ data }) => setScreenings(data.results ?? data)).catch(() => setScreenings([]));
    const params = new URLSearchParams(window.location.search);
    setSelectedId(Number(params.get("id") || 0));
  }, []);

  const selected = screenings.find((item) => item.id === selectedId) ?? screenings[0];
  const filtered = useMemo(() => {
    if (!deferredSearch) return screenings;
    return screenings.filter((item) =>
      [item.client.full_name, item.client.country, item.risk_level].join(" ").toLowerCase().includes(deferredSearch.toLowerCase())
    );
  }, [screenings, deferredSearch]);

  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-white/10 bg-white/5 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-slate-300">{t("screeningHistory")}</p>
            <h2 className="text-xl font-semibold text-white">{t("results")}</h2>
          </div>
          <input
            placeholder={t("search")}
            className="w-full max-w-sm rounded-lg border border-white/10 bg-ink/70 px-4 py-3 text-white"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <ResultsTable screenings={filtered} />
      </section>

      {selected ? (
        <section className="rounded-lg border border-white/10 bg-white/5 p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm text-slate-300">#{selected.id}</p>
              <h3 className="text-lg font-semibold text-white">{selected.client.full_name || selected.client.country}</h3>
            </div>
            <RiskBadge level={selected.risk_level} />
          </div>
          <div className="overflow-hidden rounded-lg border border-white/10">
            <table className="min-w-full divide-y divide-white/10 text-sm">
              <thead className="bg-white/5 text-left text-slate-300">
                <tr>
                  <th className="px-4 py-3">{t("source")}</th>
                  <th className="px-4 py-3">{t("aliases")}</th>
                  <th className="px-4 py-3">{t("score")}</th>
                  <th className="px-4 py-3">{t("risk")}</th>
                  <th className="px-4 py-3">{t("remarks")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {(selected.grouped_matches && selected.grouped_matches.length ? selected.grouped_matches : [{ key: "all", matches: selected.matches }]).map((group) => (
                  <React.Fragment key={group.key}>
                    <tr className="bg-white/3 text-slate-300">
                      <td className="px-4 py-2 font-medium" colSpan={5}>
                        <div className="flex items-center justify-between">
                          <div>
                            {group.url ? (
                              <a href={group.url} className="text-teal underline" target="_blank" rel="noreferrer">
                                {group.title || group.url}
                              </a>
                            ) : (
                              <span>{group.source_code || "Other"}</span>
                            )}
                            {group.snippet ? (
                              <div className="text-xs text-slate-400 mt-1">
                                <span className="rounded bg-white/5 px-1 py-0.5 text-xs">{group.snippet}</span>
                              </div>
                            ) : null}
                          </div>
                          {group.url ? (
                            <a
                              href={group.url}
                              target="_blank"
                              rel="noreferrer"
                              className="ml-4 inline-flex items-center gap-2 rounded-md border border-teal/30 px-3 py-2 text-teal text-sm hover:bg-teal/5"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-90">
                                <path d="M14 3h7v7" />
                                <path d="M10 14L21 3" />
                                <path d="M21 14v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h7" />
                              </svg>
                              {t("openUrl") || "Abrir URL"}
                            </a>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                    {group.matches.map((match) => (
                      <tr key={match.id} className="text-slate-100">
                        <td className="px-4 py-4">
                          <div className="font-medium">{match.source_code}</div>
                          <div className="text-xs text-slate-400">{match.matched_name}</div>
                        </td>
                        <td className="px-4 py-4 text-slate-300">{match.aliases?.join(", ") || "-"}</td>
                        <td className="px-4 py-4">{match.score}%</td>
                        <td className="px-4 py-4">
                          <RiskBadge level={match.risk_level} />
                        </td>
                        <td className="px-4 py-4 text-slate-300">{match.remarks || selected.recommendation}</td>
                      </tr>
                    ))}
                  </React.Fragment>
                ))}
                {!selected.matches.length ? (
                  <tr>
                    <td className="px-4 py-6 text-center text-slate-400" colSpan={5}>
                      {t("noData")}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </div>
  );
}
