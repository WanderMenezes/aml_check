import { ReactNode } from "react";

export function StatCard({
  eyebrow,
  value,
  accent,
  icon
}: {
  eyebrow: string;
  value: string | number;
  accent: string;
  icon: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-5 shadow-glow">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-300">{eyebrow}</p>
        <div className={`rounded-lg p-3 ${accent}`}>{icon}</div>
      </div>
      <p className="mt-8 text-3xl font-semibold text-white">{value}</p>
    </div>
  );
}
