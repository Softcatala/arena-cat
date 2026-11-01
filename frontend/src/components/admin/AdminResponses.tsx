import { useCallback, useEffect, useState } from "react";

import { api } from "../../api";
import type { AdminResponse } from "../../types";
import { Field, INPUT } from "../Field";
import {
  ActionButton,
  Badge,
  ConfirmDelete,
  ErrorNote,
  messageOf,
  PAGE_SIZE,
  Pager,
  TABLE,
  TD,
  TH,
} from "./shared";

type Tri = "" | "true" | "false";

const toBool = (value: Tri): boolean | "" => (value === "" ? "" : value === "true");

export default function AdminResponses() {
  const [responses, setResponses] = useState<AdminResponse[] | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [promptId, setPromptId] = useState("");
  const [model, setModel] = useState("");
  const [active, setActive] = useState<Tri>("");
  const [ranked, setRanked] = useState<Tri>("");
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<number | null>(null);
  const [form, setForm] = useState({ prompt_id: "", model: "", text: "" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const page = await api.admin.responses(PAGE_SIZE, offset, {
        prompt_id: promptId ? Number(promptId) : "",
        model: model.trim(),
        active: toBool(active),
        included_in_ranking: toBool(ranked),
      });
      setResponses(page.items);
      setTotal(page.total);
      setError(null);
    } catch (err) {
      setError(messageOf(err));
    }
  }, [offset, promptId, model, active, ranked]);

  useEffect(() => {
    void load();
  }, [load]);

  function filter<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value);
      setOffset(0);
    };
  }

  async function change(
    item: AdminResponse,
    changes: { active?: boolean; included_in_ranking?: boolean },
  ) {
    try {
      const updated = await api.admin.updateResponse(item.id, changes);
      setResponses(
        (current) => current?.map((row) => (row.id === updated.id ? updated : row)) ?? null,
      );
      setError(null);
    } catch (err) {
      setError(messageOf(err));
    }
  }

  async function remove(item: AdminResponse) {
    try {
      await api.admin.deleteResponse(item.id);
      setConfirming(null);
      await load();
    } catch (err) {
      setConfirming(null);
      setError(messageOf(err));
    }
  }

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      await api.admin.createResponse({ ...form, prompt_id: Number(form.prompt_id) });
      setForm({ prompt_id: form.prompt_id, model: "", text: "" });
      setOffset(0);
      await load();
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="admin-responses" className="space-y-4">
      <div>
        <h2 id="admin-responses" className="text-xl font-bold">
          Inferències
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Una inferència desactivada no es mostra als avaluadors. Una de no inclosa al rànquing
          conserva els vots però no compten. Només s'esborren les que no tenen vots.
        </p>
      </div>

      <form
        onSubmit={(event) => void create(event)}
        className="space-y-3 rounded-lg border border-slate-200 bg-white p-4"
      >
        <h3 className="font-semibold">Nova inferència</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Id del prompt">
            <input
              className={INPUT}
              inputMode="numeric"
              pattern="[0-9]+"
              value={form.prompt_id}
              onChange={(event) => setForm({ ...form, prompt_id: event.target.value })}
              required
            />
          </Field>
          <Field label="Model">
            <input
              className={INPUT}
              value={form.model}
              onChange={(event) => setForm({ ...form, model: event.target.value })}
              required
            />
          </Field>
        </div>
        <Field label="Resposta">
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
          Afegeix la inferència
        </button>
      </form>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm font-medium">
          Prompt
          <input
            value={promptId}
            inputMode="numeric"
            onChange={(event) => filter(setPromptId)(event.target.value.replace(/\D/g, ""))}
            placeholder="Tots"
            className="mt-1 block w-24 rounded-md border border-slate-300 bg-white px-3 py-2"
          />
        </label>
        <label className="text-sm font-medium">
          Model
          <input
            value={model}
            onChange={(event) => filter(setModel)(event.target.value)}
            placeholder="Tots"
            className="mt-1 block w-44 rounded-md border border-slate-300 bg-white px-3 py-2"
          />
        </label>
        {(
          [
            ["Activa", active, filter(setActive), "Actives", "Inactives"],
            ["Al rànquing", ranked, filter(setRanked), "Incloses", "Excloses"],
          ] as const
        ).map(([label, value, setter, yes, no]) => (
          <label key={label} className="text-sm font-medium">
            {label}
            <select
              value={value}
              onChange={(event) => setter(event.target.value as Tri)}
              className="mt-1 block rounded-md border border-slate-300 bg-white px-3 py-2"
            >
              <option value="">Totes</option>
              <option value="true">{yes}</option>
              <option value="false">{no}</option>
            </select>
          </label>
        ))}
      </div>

      <ErrorNote message={error} />
      {responses === null ? (
        <p className="text-slate-500">Carregant…</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className={TABLE}>
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className={TH}>Id</th>
                <th className={TH}>Prompt</th>
                <th className={TH}>Model</th>
                <th className={TH}>Resposta</th>
                <th className={TH}>Vots</th>
                <th className={TH}>Estat</th>
                <th className={TH}>
                  <span className="sr-only">Accions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {responses.map((item) => (
                <tr key={item.id}>
                  <td className={TD}>{item.id}</td>
                  <td className={TD}>{item.prompt_id}</td>
                  <td className={TD}>{item.model}</td>
                  <td className={`${TD} max-w-sm`}>
                    <span className="line-clamp-2" title={item.text}>
                      {item.text}
                    </span>
                  </td>
                  <td className={TD}>{item.vote_count}</td>
                  <td className={`${TD} space-x-1`}>
                    <Badge tone={item.active ? "ok" : "off"}>
                      {item.active ? "Activa" : "Inactiva"}
                    </Badge>
                    <Badge tone={item.included_in_ranking ? "ok" : "warn"}>
                      {item.included_in_ranking ? "Al rànquing" : "Exclosa"}
                    </Badge>
                  </td>
                  <td className={`${TD} space-x-1 text-right`}>
                    <ActionButton onClick={() => void change(item, { active: !item.active })}>
                      {item.active ? "Desactiva" : "Activa"}
                    </ActionButton>
                    <ActionButton
                      onClick={() =>
                        void change(item, { included_in_ranking: !item.included_in_ranking })
                      }
                    >
                      {item.included_in_ranking ? "Exclou" : "Inclou"}
                    </ActionButton>
                    <ConfirmDelete
                      disabled={item.vote_count > 0}
                      title={item.vote_count > 0 ? "Té vots associats" : undefined}
                      confirming={confirming === item.id}
                      setConfirming={(value) => setConfirming(value ? item.id : null)}
                      onConfirm={() => void remove(item)}
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
