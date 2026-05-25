import clsx from "clsx";

import { RiskLevel } from "@/lib/types";

const theme: Record<RiskLevel, string> = {
  LOW: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  MEDIUM: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  HIGH: "bg-orange-500/15 text-orange-200 border-orange-400/40",
  CRITICAL: "bg-rose-500/15 text-rose-200 border-rose-400/40"
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span className={clsx("rounded-full border px-2.5 py-1 text-xs font-semibold tracking-[0.18em]", theme[level])}>
      {level}
    </span>
  );
}
