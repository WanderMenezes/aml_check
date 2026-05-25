"use client";

import { useAppShell } from "@/providers/app-shell-provider";

export function TrendChart({ values }: { values: number[] }) {
  const { t } = useAppShell();
  const maxValue = Math.max(...values, 1);
  const points = values
    .map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${90 - (value / maxValue) * 70}`)
    .join(" ");

  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-5">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">{t("riskFlow")}</p>
          <h3 className="text-lg font-semibold text-white">{t("activity30")}</h3>
        </div>
        <span className="rounded-lg border border-teal/30 bg-teal/10 px-3 py-1 text-xs font-medium text-teal">{t("live")}</span>
      </div>
      {values.length ? (
        <svg viewBox="0 0 100 100" className="h-48 w-full">
          <defs>
            <linearGradient id="trend" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#0FB7A7" />
              <stop offset="100%" stopColor="#DAB66B" />
            </linearGradient>
          </defs>
          <polyline fill="none" stroke="url(#trend)" strokeWidth="3" points={points} />
          {values.map((value, index) => (
            <circle
              key={`${value}-${index}`}
              cx={(index / Math.max(values.length - 1, 1)) * 100}
              cy={90 - (value / maxValue) * 70}
              r="1.7"
              fill="#0FB7A7"
            />
          ))}
        </svg>
      ) : (
        <div className="flex h-48 items-center justify-center text-sm text-slate-400">{t("noData")}</div>
      )}
    </div>
  );
}
