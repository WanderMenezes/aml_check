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
  return (
    <div className="mt-3 rounded-md bg-white/3 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <a href={group.url} target="_blank" rel="noreferrer" className="text-teal underline break-words">
            {group.title || group.url}
          </a>
          <div className="mt-1 text-xs text-slate-400">{group.source_code || ""}</div>
          {group.snippet ? <div className="mt-2 text-sm text-slate-300">{highlight(group.snippet, query)}</div> : null}
        </div>
        <div className="shrink-0 text-right">
          <div className="text-sm font-semibold text-slate-200">{group.score ? `${group.score}%` : ""}</div>
        </div>
      </div>
    </div>
  );
}

export default ExternalResultGroup;
