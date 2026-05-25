"use client";

import React, { useEffect, useRef, useState } from "react";
import ExternalResultGroup from "./external-result-group";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  results: any[];
  query: string;
}

export function ExternalResultsModal({ open, onClose, results, query }: ModalProps) {
  const [mounted, setMounted] = useState(open);
  const [visible, setVisible] = useState(open);
  const closeBtnRef = useRef<HTMLButtonElement | null>(null);
  const lastActiveRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (open) {
      lastActiveRef.current = document.activeElement as HTMLElement | null;
      setMounted(true);
      // small delay for enter animation
      requestAnimationFrame(() => setVisible(true));
      // block background scroll
      document.body.style.overflow = "hidden";
    } else if (mounted) {
      // trigger exit animation
      setVisible(false);
      // restore scroll after animation
      const t = setTimeout(() => {
        setMounted(false);
        document.body.style.overflow = "";
      }, 200);
      return () => clearTimeout(t);
    }
  }, [open]);

  useEffect(() => {
    if (mounted) {
      // focus the close button for accessibility
      setTimeout(() => closeBtnRef.current?.focus(), 50);
    } else {
      // restore focus to last active element
      lastActiveRef.current?.focus?.();
    }
  }, [mounted]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        handleClose();
      }
    }
    if (mounted) {
      window.addEventListener("keydown", onKey);
    }
    return () => window.removeEventListener("keydown", onKey);
  }, [mounted]);

  function handleClose() {
    // animate out then call onClose
    setVisible(false);
    setTimeout(() => {
      onClose();
      document.body.style.overflow = "";
    }, 200);
  }

  if (!mounted) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true">
      <div
        className={`absolute inset-0 transition-opacity ${visible ? "opacity-100" : "opacity-0"}`}
        style={{ backgroundColor: "rgba(0,0,0,0.6)" }}
        onClick={handleClose}
        aria-hidden
      />
      <div
        className={`relative z-10 w-11/12 max-w-3xl transform transition-all duration-200 ${
          visible ? "opacity-100 scale-100" : "opacity-0 scale-95"
        } rounded-lg bg-ink/95 p-4 text-white`}
        role="document"
      >
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Resultados externos</h3>
          <button
            ref={closeBtnRef}
            onClick={handleClose}
            className="text-sm text-slate-300 hover:text-white"
            aria-label="Fechar resultados externos"
          >
            Fechar
          </button>
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
