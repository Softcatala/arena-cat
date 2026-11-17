import { useCallback, useEffect, useState } from "react";

import { api } from "../../api";
import type { AdminPrompt, Category } from "../../types";
import {
  ActionButton,
  Badge,
  ErrorNote,
  messageOf,
  PAGE_SIZE,
  Pager,
  TABLE,
  TD,
  TH,
} from "./shared";

export default function AdminPrompts({ categories }: { categories: Category[] }) {
  const [prompts, setPrompts] = useState<AdminPrompt[] | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [version, setVersion] = useState("");
  const [category, setCategory] = useState("");
  const [activeFilter, setActiveFilter] = useState<"" | "true" | "false">("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const page = await api.admin.prompts(PAGE_SIZE, offset, {
        version: version.trim(),
        category_code: category,
        active: activeFilter === "" ? "" : activeFilter === "true",
      });
      setPrompts(page.items);
      setTotal(page.total);
      setError(null);
    } catch (err) {
      setError(messageOf(err));
    }
  }, [offset, version, category, activeFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleActive(prompt: AdminPrompt) {
    try {
      const updated = await api.admin.updatePrompt(prompt.id, { active: !prompt.active });
      setPrompts(
        (current) => current?.map((item) => (item.id === updated.id ? updated : item)) ?? null,
      );
      setError(null);
    } catch (err) {
      setError(messageOf(err));
    }
  }

  return (
    <section aria-labelledby="admin-prompts" className="space-y-4">
      <div>
        <h2 id="admin-prompts" className="text-xl font-bold">
          Prompts
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Un prompt desactivat no es serveix i el rànquing deixa de comptar-lo; si n'hi ha una
          versió anterior, hi torna.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm font-medium">
          Versió
          <input
            value={version}
            onChange={(event) => {
              setVersion(event.target.value);
              setOffset(0);
            }}
            placeholder="Totes"
            className="mt-1 block w-28 rounded-md border border-slate-300 bg-white px-3 py-2"
          />
        </label>
        <label className="text-sm font-medium">
          Categoria
          <select
            value={category}
            onChange={(event) => {
              setCategory(event.target.value);
              setOffset(0);
            }}
            className="mt-1 block rounded-md border border-slate-300 bg-white px-3 py-2"
          >
            <option value="">Totes</option>
            {categories.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium">
          Estat
          <select
            value={activeFilter}
            onChange={(event) => {
              setActiveFilter(event.target.value as "" | "true" | "false");
              setOffset(0);
            }}
            className="mt-1 block rounded-md border border-slate-300 bg-white px-3 py-2"
          >
            <option value="">Tots</option>
            <option value="true">Actius</option>
            <option value="false">Inactius</option>
          </select>
        </label>
      </div>

      <ErrorNote message={error} />
      {prompts === null ? (
        <p className="text-slate-500">Carregant…</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className={TABLE}>
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className={TH}>Id</th>
                <th className={TH}>Versió</th>
                <th className={TH}>Codi</th>
                <th className={TH}>Text</th>
                <th className={TH}>Inferències</th>
                <th className={TH}>Estat</th>
                <th className={TH}>
                  <span className="sr-only">Accions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {prompts.map((prompt) => (
                <tr key={prompt.id}>
                  <td className={TD}>{prompt.id}</td>
                  <td className={TD}>{prompt.version}</td>
                  <td className={TD}>{prompt.code}</td>
                  <td className={`${TD} max-w-md`}>
                    <span className="line-clamp-2" title={prompt.text}>
                      {prompt.text}
                    </span>
                  </td>
                  <td className={TD}>{prompt.response_count}</td>
                  <td className={TD}>
                    <Badge tone={prompt.active ? "ok" : "off"}>
                      {prompt.active ? "Actiu" : "Inactiu"}
                    </Badge>
                  </td>
                  <td className={`${TD} space-x-1 whitespace-nowrap text-right`}>
                    <ActionButton onClick={() => void toggleActive(prompt)}>
                      {prompt.active ? "Desactiva" : "Activa"}
                    </ActionButton>
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
