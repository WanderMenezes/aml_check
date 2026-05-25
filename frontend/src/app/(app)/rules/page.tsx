"use client";

import { Save } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import { RiskLevel, RiskRule } from "@/lib/types";
import { useAppShell } from "@/providers/app-shell-provider";

interface CountryRule {
  id: number;
  name: string;
  risk_level: RiskLevel;
  is_blocked: boolean;
  notes: string;
}

export default function RulesPage() {
  const { t } = useAppShell();
  const [rules, setRules] = useState<RiskRule[]>([]);
  const [countries, setCountries] = useState<CountryRule[]>([]);
  const [countrySearch, setCountrySearch] = useState("");

  const load = () => {
    api.get("/intelligence/rules/").then(({ data }) => setRules(data.results ?? data)).catch(() => setRules([]));
    api.get("/intelligence/countries/").then(({ data }) => setCountries(data.results ?? data)).catch(() => setCountries([]));
  };

  useEffect(() => {
    load();
  }, []);

  const updateRule = async (rule: RiskRule, patch: Partial<RiskRule>) => {
    const next = { ...rule, ...patch };
    setRules((current) => current.map((item) => (item.id === rule.id ? next : item)));
    await api.patch(`/intelligence/rules/${rule.id}/`, patch);
  };

  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-white/10 bg-white/5 p-5">
        <div className="mb-5">
          <p className="text-sm text-slate-300">{t("threshold")}</p>
          <h2 className="text-xl font-semibold text-white">{t("rulesEngine")}</h2>
        </div>
        <div className="overflow-hidden rounded-lg border border-white/10">
          <table className="min-w-full divide-y divide-white/10 text-sm">
            <thead className="bg-white/5 text-left text-slate-300">
              <tr>
                <th className="px-4 py-3">{t("rules")}</th>
                <th className="px-4 py-3">{t("source")}</th>
                <th className="px-4 py-3">{t("riskLevel")}</th>
                <th className="px-4 py-3">{t("threshold")}</th>
                <th className="px-4 py-3">{t("status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {rules.map((rule) => (
                <tr key={rule.id} className="text-slate-100">
                  <td className="px-4 py-4">{rule.name}</td>
                  <td className="px-4 py-4">{rule.source_code || rule.condition_type}</td>
                  <td className="px-4 py-4">
                    <select
                      className="rounded-lg border border-white/10 bg-ink px-3 py-2 text-white"
                      value={rule.risk_level}
                      onChange={(event) => updateRule(rule, { risk_level: event.target.value as RiskLevel })}
                    >
                      {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as RiskLevel[]).map((level) => (
                        <option key={level}>{level}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-4">{rule.target_value || "-"}</td>
                  <td className="px-4 py-4">
                    <label className="inline-flex items-center gap-2">
                      <input type="checkbox" checked={rule.enabled} onChange={(event) => updateRule(rule, { enabled: event.target.checked })} />
                      <span>{rule.enabled ? t("enabled") : t("disabled")}</span>
                    </label>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-white/10 bg-white/5 p-5">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold text-white">{t("blockedCountries")}</h2>
          <input
            className="w-full max-w-sm rounded-lg border border-white/10 bg-ink/70 px-4 py-3 text-white"
            placeholder={t("search")}
            value={countrySearch}
            onChange={(event) => setCountrySearch(event.target.value)}
          />
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {countries
            .filter((country) => country.name.toLowerCase().includes(countrySearch.toLowerCase()))
            .slice(0, 24)
            .map((country) => (
            <div key={country.id} className="rounded-lg border border-white/10 bg-ink/60 p-4">
              <p className="font-medium text-white">{country.name}</p>
              <p className="mt-1 text-sm text-slate-400">{country.risk_level}</p>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <select
                  className="rounded-lg border border-white/10 bg-ink px-3 py-2 text-white"
                  value={country.risk_level}
                  onChange={async (event) => {
                    await api.patch(`/intelligence/countries/${country.id}/`, { risk_level: event.target.value });
                    load();
                  }}
                >
                  {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as RiskLevel[]).map((level) => (
                    <option key={level}>{level}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={async () => {
                    await api.patch(`/intelligence/countries/${country.id}/`, { is_blocked: !country.is_blocked });
                    load();
                  }}
                  className="inline-flex items-center gap-2 rounded-lg border border-teal/30 px-3 py-2 text-sm text-teal"
                >
                  <Save size={14} />
                  {country.is_blocked ? t("blocked") : t("allowed")}
                </button>
              </div>
            </div>
          ))}
          {!countries.length ? <p className="text-sm text-slate-400">{t("noData")}</p> : null}
        </div>
      </section>
    </div>
  );
}
