import { useCallback, useEffect, useState } from "react";

import { api } from "../../api";
import type { AdminUser } from "../../types";
import {
  ActionButton,
  Badge,
  ErrorNote,
  formatDate,
  messageOf,
  PAGE_SIZE,
  Pager,
  TABLE,
  TD,
  TH,
} from "./shared";

export default function AdminUsers({ selfEmail }: { selfEmail: string | null }) {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const page = await api.admin.users(PAGE_SIZE, offset);
      setUsers(page.items);
      setTotal(page.total);
      setError(null);
    } catch (err) {
      setError(messageOf(err));
    }
  }, [offset]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleBlock(user: AdminUser) {
    try {
      const updated = user.blocked_at
        ? await api.admin.unblockUser(user.id)
        : await api.admin.blockUser(user.id);
      setUsers(
        (current) => current?.map((item) => (item.id === updated.id ? updated : item)) ?? null,
      );
      setError(null);
    } catch (err) {
      setError(messageOf(err));
    }
  }

  return (
    <section aria-labelledby="admin-users" className="space-y-4">
      <div>
        <h2 id="admin-users" className="text-xl font-bold">
          Usuaris
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Bloquejar un usuari li tanca les sessions i li impedeix tornar a entrar. Els seus vots es
          conserven.
        </p>
      </div>
      <ErrorNote message={error} />
      {users === null ? (
        <p className="text-slate-500">Carregant…</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className={TABLE}>
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className={TH}>Id</th>
                <th className={TH}>Correu</th>
                <th className={TH}>Estat</th>
                <th className={TH}>Alta</th>
                <th className={TH}>
                  <span className="sr-only">Accions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((user) => (
                <tr key={user.id}>
                  <td className={TD}>{user.id}</td>
                  <td className={TD}>
                    {user.email ?? <em className="text-slate-400">anonimitzat</em>}
                  </td>
                  <td className={`${TD} space-x-1`}>
                    {user.is_admin && <Badge tone="ok">Admin</Badge>}
                    {user.blocked_at && <Badge tone="warn">Bloquejat</Badge>}
                    {user.deleted_at && <Badge tone="off">De baixa</Badge>}
                    {user.qualified_at && <Badge tone="ok">Acreditat</Badge>}
                  </td>
                  <td className={TD}>{formatDate(user.created_at)}</td>
                  <td className={`${TD} text-right`}>
                    {!user.deleted_at && user.email !== selfEmail && (
                      <ActionButton
                        danger={!user.blocked_at}
                        onClick={() => void toggleBlock(user)}
                      >
                        {user.blocked_at ? "Desbloqueja" : "Bloqueja"}
                      </ActionButton>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pager total={total} offset={offset} onChange={setOffset} />
    </section>
  );
}
