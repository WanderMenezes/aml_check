"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { useAppShell } from "@/providers/app-shell-provider";

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user } = useAppShell();

  useEffect(() => {
    const auth = window.localStorage.getItem("aml-auth");
    if (!auth) router.push("/login");
  }, [router, user]);

  return (
    <div className="min-h-screen bg-ink bg-radial px-4 py-5 text-slate-100 lg:px-6">
      <div className="mx-auto flex max-w-[1600px] gap-5">
        <Sidebar />
        <main className="flex-1 space-y-5">
          <Topbar />
          {children}
        </main>
      </div>
    </div>
  );
}
