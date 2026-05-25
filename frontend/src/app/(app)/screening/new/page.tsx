"use client";

import { useState } from "react";

import { ResultsTable } from "@/components/screening/results-table";
import { ScreeningForm } from "@/components/screening/screening-form";
import { api } from "@/lib/api/client";
import { ScreeningRequest } from "@/lib/types";
import { useAppShell } from "@/providers/app-shell-provider";

export default function NewScreeningPage() {
  const { t } = useAppShell();
  const [screenings, setScreenings] = useState<ScreeningRequest[]>([]);
  const [error, setError] = useState("");

  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-white/10 bg-white/5 p-5">
        <div className="mb-4">
          <p className="text-sm text-slate-300">{t("searchClient")}</p>
          <h2 className="text-xl font-semibold text-white">{t("newScreening")}</h2>
        </div>
        <ScreeningForm
          onSubmit={async (payload) => {
            setError("");
            try {
              const { data } = await api.post("/screening/requests/run/", payload);
              setScreenings((current) => [data, ...current]);
            } catch {
              setError(t("invalidScreeningInput"));
            }
          }}
        />
        {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
      </section>
      <ResultsTable screenings={screenings} />
    </div>
  );
}
