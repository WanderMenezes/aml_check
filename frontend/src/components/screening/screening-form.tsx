"use client";

import { SearchCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { api } from "@/lib/api/client";
import ExternalResultsModal from "./external-results-modal";

import { useAppShell } from "@/providers/app-shell-provider";

interface ScreeningFormProps {
  onSubmit: (payload: { client: { full_name?: string; country?: string } }) => Promise<void>;
}

function hasCompleteName(value: string) {
  const tokens = value.trim().split(/\s+/).filter(Boolean);
  return tokens.length >= 2 && tokens.every((token) => token.replace(/[-']/g, "").length >= 2) && !/\d/.test(value);
}

export function ScreeningForm({ onSubmit }: ScreeningFormProps) {
  const { t } = useAppShell();
  const [fullName, setFullName] = useState("");
  const [country, setCountry] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [externalLoading, setExternalLoading] = useState(false);
  const [externalResults, setExternalResults] = useState<any[] | null>(null);
  const [externalQuery, setExternalQuery] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  const isValid = useMemo(() => {
    const hasName = fullName.trim().length > 0;
    const hasCountry = country.trim().length > 0;
    if (!hasName && !hasCountry) return false;
    if (hasName && !hasCompleteName(fullName)) return false;
    if (hasCountry && country.trim().length < 3) return false;
    return true;
  }, [country, fullName]);

  return (
    <form
      className="grid gap-4 rounded-lg border border-white/10 bg-white/5 p-5 lg:grid-cols-[1fr_0.8fr_auto]"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!isValid) {
          setError(t("invalidScreeningInput"));
          return;
        }
        setError("");
        setSubmitting(true);
        try {
          await onSubmit({ client: { full_name: fullName.trim(), country: country.trim() } });
          setFullName("");
          setCountry("");
        } finally {
          setSubmitting(false);
        }
      }}
    >
      <label className="space-y-2">
        <span className="text-sm text-slate-300">{t("fullName")}</span>
        <input
          className="w-full rounded-lg border border-white/10 bg-ink/70 px-4 py-3 text-white outline-none transition focus:border-teal/60"
          value={fullName}
          placeholder="Mohamed Ali"
          onChange={(event) => setFullName(event.target.value)}
        />
        <span className="block text-xs text-slate-400">{t("personSearchRule")}</span>
      </label>
      <label className="space-y-2">
        <span className="text-sm text-slate-300">{t("country")}</span>
        <input
          className="w-full rounded-lg border border-white/10 bg-ink/70 px-4 py-3 text-white outline-none transition focus:border-teal/60"
          value={country}
          placeholder="Syria"
          onChange={(event) => setCountry(event.target.value)}
        />
        <span className="block text-xs text-slate-400">{t("countrySearchRule")}</span>
      </label>
      <div className="flex items-end">
        <button
          type="submit"
          disabled={submitting || !isValid}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-teal px-4 py-3 font-semibold text-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60 lg:w-auto"
        >
          <SearchCheck size={18} />
          {submitting ? t("loading") : t("runScreening")}
        </button>
        <button
          type="button"
          disabled={!isValid || externalLoading}
          onClick={async () => {
            const q = fullName.trim() || country.trim();
            if (!q) return;
            setExternalLoading(true);
            setExternalResults(null);
            setExternalQuery(q);
            try {
              const { data } = await api.post("/screening/external-search/", { query: q });
              setExternalResults(data.groups || []);
              setModalOpen(true);
            } catch (err) {
              setExternalResults([]);
              setModalOpen(true);
            } finally {
              setExternalLoading(false);
            }
          }}
          className="ml-2 inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/3 px-4 py-3 text-sm text-white disabled:opacity-60"
        >
          {externalLoading ? t("loading") : "Buscar nas URLs"}
        </button>
      </div>
      {error ? <p className="lg:col-span-3 text-sm text-rose-300">{error}</p> : null}
      <ExternalResultsModal open={modalOpen} onClose={() => setModalOpen(false)} results={externalResults || []} query={externalQuery} />
    </form>
  );
}
