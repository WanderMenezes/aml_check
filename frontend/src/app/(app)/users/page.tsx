"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import { UserAccount } from "@/lib/types";
import { useAppShell } from "@/providers/app-shell-provider";

export default function UsersPage() {
  const { t } = useAppShell();
  const [users, setUsers] = useState<UserAccount[]>([]);

  const load = () => {
    api.get("/users/").then(({ data }) => setUsers(data.results ?? data)).catch(() => setUsers([]));
  };

  useEffect(() => {
    load();
  }, []);

  const updateUser = async (user: UserAccount, patch: Partial<UserAccount>) => {
    setUsers((current) => current.map((item) => (item.id === user.id ? { ...item, ...patch } : item)));
    await api.patch(`/users/${user.id}/`, patch);
    load();
  };

  return (
    <section className="rounded-lg border border-white/10 bg-white/5 p-5">
      <div className="mb-5">
        <p className="text-sm text-slate-300">{t("roles")}</p>
        <h2 className="text-xl font-semibold text-white">{t("usersManagement")}</h2>
      </div>
      <div className="overflow-hidden rounded-lg border border-white/10">
        <table className="min-w-full divide-y divide-white/10 text-sm">
          <thead className="bg-white/5 text-left text-slate-300">
            <tr>
              <th className="px-4 py-3">{t("email")}</th>
              <th className="px-4 py-3">{t("role")}</th>
              <th className="px-4 py-3">{t("status")}</th>
              <th className="px-4 py-3">{t("language")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {users.map((user) => (
              <tr key={user.id} className="text-slate-100">
                <td className="px-4 py-4">
                  <div className="font-medium">{user.email}</div>
                  <div className="text-xs text-slate-400">{user.permissions.join(", ")}</div>
                </td>
                <td className="px-4 py-4">
                  <select
                    className="rounded-lg border border-white/10 bg-ink px-3 py-2 text-white"
                    value={user.role}
                    onChange={(event) => updateUser(user, { role: event.target.value })}
                  >
                    {["ADMIN", "COMPLIANCE_OFFICER", "ANALYST", "VIEWER"].map((role) => (
                      <option key={role}>{role}</option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-4">
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={user.is_active} onChange={(event) => updateUser(user, { is_active: event.target.checked })} />
                    <span>{user.is_active ? t("active") : t("inactive")}</span>
                  </label>
                </td>
                <td className="px-4 py-4">{user.preferred_language}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
