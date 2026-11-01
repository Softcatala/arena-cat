import { useState } from "react";

import { api } from "../../api";
import type { ImportResult } from "../../types";
import { Field, INPUT } from "../Field";
import { Badge, ErrorNote, messageOf } from "./shared";

/** El servidor rebutja fitxers de més de 200.000 caràcters. */
const MAX_CHARS = 200_000;

export default function ImportYaml({ onImported }: { onImported: () => void }) {
  const [version, setVersion] = useState("v1");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy || files.length === 0) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const contents = await Promise.all(
        files.map(async (file) => ({ name: file.name, content: await file.text() })),
      );
      const oversized = contents.filter((item) => item.content.length > MAX_CHARS);
      const sendable = contents.filter((item) => item.content.length <= MAX_CHARS);
      const outcome = await api.admin.importResponses(version.trim(), sendable);
      for (const item of oversized) {
        outcome.errors += 1;
        outcome.files.push({ name: item.name, status: "error", detail: "El fitxer és massa gran" });
      }
      setResult(outcome);
      setFiles([]);
      if (outcome.inserted > 0) onImported();
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  const problems = result?.files.filter((item) => item.status === "error") ?? [];

  return (
    <form
      onSubmit={(event) => void submit(event)}
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-4"
    >
      <div>
        <h3 className="font-semibold">Importa fitxers YAML</h3>
        <p className="mt-1 text-sm text-slate-600">
          Els fitxers que genera la canonada d'inferència. Cal que els prompts de la versió ja
          existeixin. Els fitxers repetits s'ometen i els que canvien una resposta existent es
          rebutgen.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-[8rem_1fr]">
        <Field label="Versió">
          <input
            className={INPUT}
            value={version}
            onChange={(event) => setVersion(event.target.value)}
            required
          />
        </Field>
        <Field label="Fitxers" hint={files.length ? `${files.length} fitxers triats` : undefined}>
          <input
            type="file"
            multiple
            accept=".yaml,.yml"
            onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
            className="block w-full text-sm file:mr-3 file:rounded-md file:border file:border-slate-300 file:bg-white file:px-3 file:py-2 file:text-sm"
          />
        </Field>
      </div>
      <button
        type="submit"
        disabled={busy || files.length === 0}
        className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {busy ? "Important…" : "Importa"}
      </button>

      <ErrorNote message={error} />
      {result && (
        <div className="space-y-2 text-sm" role="status">
          <p className="space-x-2">
            <Badge tone="ok">{result.inserted} inserits</Badge>
            <Badge tone="off">{result.skipped} omesos</Badge>
            <Badge tone={result.errors > 0 ? "warn" : "off"}>{result.errors} errors</Badge>
          </p>
          {problems.length > 0 && (
            <ul className="max-h-48 space-y-1 overflow-y-auto rounded-md bg-red-50 p-3 text-red-700">
              {problems.map((item) => (
                <li key={item.name}>
                  <strong>{item.name}</strong>: {item.detail}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </form>
  );
}
