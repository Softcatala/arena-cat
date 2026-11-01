import { useCallback, useEffect, useState } from "react";

import { api } from "../../api";
import type { AdminPrompt, Category } from "../../types";
import { Field, INPUT } from "../Field";
import { ConfirmDelete, ErrorNote, messageOf, PAGE_SIZE, Pager, TABLE, TD, TH } from "./shared";

const EMPTY = { version: "v1", code: "", category_code: "", text: "" };

export default function AdminPrompts({ categories }: { categories: Category[] }) {
  const [prompts, setPrompts] = useState<AdminPrompt[] | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [version, setVersion] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<number | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const page = await api.admin.prompts(PAGE_SIZE, offset, {
        version: version.trim(),
        category_code: category,
      });
      setPrompts(page.items);
      setTotal(page.total);
      setError(null);
    } catch (err) {
      setError(messageOf(err));
    }
  }, [offset, version, category]);

  useEffect(() => {
    void load();
  }, [load]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      await api.admin.createPrompt({
        ...form,
        category_code: form.category_code || categories[0]?.code,
      });
      setForm({ ...EMPTY, version: form.version, category_code: form.category_code });
      setOffset(0);
      await load();
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(prompt: AdminPrompt) {
    try {
      await api.admin.deletePrompt(prompt.id);
      setConfirming(null);
      await load();
    } catch (err) {
      setConfirming(null);
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
          El contingut no es pot repetir dins d'una versió. Només s'esborren els prompts sense
          inferències.
        </p>
      </div>

      <form
        onSubmit={(event) => void create(event)}
        className="space-y-3 rounded-lg border border-slate-200 bg-white p-4"
      >
        <h3 className="font-semibold">Nou prompt</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Versió" hint="Per exemple, v2">
            <input
              className={INPUT}
              value={form.version}
              onChange={(event) => setForm({ ...form, version: event.target.value })}
              required
            />
          </Field>
          <Field label="Codi" hint="Per exemple, correccio_11">
            <input
              className={INPUT}
              value={form.code}
              onChange={(event) => setForm({ ...form, code: event.target.value })}
              required
            />
          </Field>
          <Field label="Categoria">
            <select
              className={INPUT}
              value={form.category_code || categories[0]?.code || ""}
              onChange={(event) => setForm({ ...form, category_code: event.target.value })}
            >
              {categories.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Text">
          <textarea
            className={INPUT}
            rows={4}
            value={form.text}
            onChange={(event) => setForm({ ...form, text: event.target.value })}
            required
          />
        </Field>
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          Crea el prompt
        </button>
      </form>

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
                  <td className={TD}>
                    {prompt.code}
                    <span className="block text-xs text-slate-400" title={prompt.content_sha256}>
                      {prompt.content_sha256.slice(0, 8)}
                    </span>
                  </td>
                  <td className={`${TD} max-w-md`}>
                    <span className="line-clamp-2" title={prompt.text}>
                      {prompt.text}
                    </span>
                  </td>
                  <td className={TD}>{prompt.response_count}</td>
                  <td className={`${TD} text-right`}>
                    <ConfirmDelete
                      disabled={prompt.response_count > 0}
                      title={prompt.response_count > 0 ? "Té inferències associades" : undefined}
                      confirming={confirming === prompt.id}
                      setConfirming={(value) => setConfirming(value ? prompt.id : null)}
                      onConfirm={() => void remove(prompt)}
                    />
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
