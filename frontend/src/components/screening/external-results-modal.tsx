"use client";

import React from "react";
import ExternalResultGroup from "./external-result-group";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  results: any[];
  query: string;
}

export function ExternalResultsModal({ open, onClose, results, query }: ModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative z-10 w-11/12 max-w-3xl rounded-lg bg-ink/95 p-4 text-white">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Resultados externos</h3>
          <button onClick={onClose} className="text-sm text-slate-300 hover:text-white">Fechar</button>
        </div>
        <div className="mt-3 space-y-3 max-h-96 overflow-auto pr-2">
          {results && results.length ? (
            results.map((g) => <ExternalResultGroup key={g.key} group={g} query={query} />)
          ) : (
            <p className="text-sm text-slate-400">Nenhum resultado encontrado.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default ExternalResultsModal;
