import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "../api";
import { Field, INPUT } from "./Field";

export default function DeleteAccountDialog({
  onClose,
  onDeleted,
}: {
  onClose: () => void;
  onDeleted: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const element = dialog.current!;
    element.showModal();
    return () => element.close();
  }, []);

  async function submit() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteAccount(password);
      onDeleted();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No s'ha pogut connectar amb l'API.");
      setBusy(false);
    }
  }

  return (
    <dialog
      ref={dialog}
      aria-labelledby="delete-account-title"
      aria-describedby="delete-account-description"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-sm rounded-lg bg-white p-6 text-slate-900 shadow-xl backdrop:bg-black/40"
    >
      <h2 id="delete-account-title" className="mb-3 text-xl font-semibold">
        Dona de baixa el compte
      </h2>
      <p id="delete-account-description" className="mb-4 text-sm text-slate-600">
        Perdreu l'accés al compte. Els vots i les omissions es conservaran. Introduïu la contrasenya
        actual per confirmar la baixa.
      </p>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <Field label="Contrasenya actual">
          <input
            type="password"
            autoComplete="current-password"
            required
            autoFocus
            disabled={busy}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={INPUT}
          />
        </Field>
        {error && (
          <p role="alert" className="text-sm text-brand-700">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            className="rounded-md border border-slate-300 px-4 py-2 disabled:opacity-50"
          >
            Cancel·la
          </button>
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {busy ? "S'està donant de baixa…" : "Confirma la baixa"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
