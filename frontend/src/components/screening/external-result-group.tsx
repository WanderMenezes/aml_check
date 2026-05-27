"use client";

import React from "react";

interface GroupProps {
  group: any;
  query: string;
}

function highlight(text: string | undefined, query: string) {
  if (!text) return null;
  if (!query) return text;
  try {
    const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "ig"));
    return parts.map((part, i) =>
      part.toLowerCase() === query.toLowerCase() ? (
        <mark key={i} className="bg-yellow-300/40 text-ink font-semibold">
          {part}
        </mark>
      ) : (
        <span key={i}>{part}</span>
      )
    );
  } catch (e) {
    return text;
  }
}

export function ExternalResultGroup({ group, query }: GroupProps) {
  const statusLabel = group.status === "FOUND" ? "Encontrado" : group.status || "Verificado";
  const evidenceClass =
    group.evidence_level === "Alto"
      ? "border-rose-400/40 bg-rose-500/10 text-rose-100"
      : group.evidence_level === "Medio"
        ? "border-amber-400/40 bg-amber-500/10 text-amber-100"
        : "border-white/10 bg-white/5 text-slate-200";

  return (
    <div className="mt-3 rounded-md bg-white/3 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <a href={group.url} target="_blank" rel="noreferrer" className="text-teal underline break-words">
            {group.title || group.url}
          </a>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span>{group.source_name || group.source_code || ""}</span>
            <span className="rounded border border-white/10 px-2 py-0.5 text-slate-300">{statusLabel}</span>
            {group.evidence_level ? <span className={`rounded border px-2 py-0.5 ${evidenceClass}`}>{group.evidence_level}</span> : null}
          </div>
          {group.snippet ? <div className="mt-2 text-sm text-slate-300">{highlight(group.snippet, query)}</div> : null}
          {group.decision_reason ? <div className="mt-2 text-xs text-slate-400">{group.decision_reason}</div> : null}
          {group.important_terms?.length ? (
            <div className="mt-2 flex flex-wrap gap-1">
              {group.important_terms.map((term: string) => (
                <span key={term} className="rounded border border-amber-300/30 bg-amber-300/10 px-2 py-0.5 text-xs text-amber-100">
                  {term}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <div className="shrink-0 text-right">
          <div className="text-sm font-semibold text-slate-200">{group.score ? `${group.score}%` : ""}</div>
        </div>
      </div>
    </div>
  );
}

export default ExternalResultGroup;
