import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, ApiError } from "../api";
import { Field, INPUT } from "./Field";

/** Demanar un enllaç per triar una contrasenya nova.
 *
 *  El compte enrere del reenviament és l'espera que comunica el backend (és configurable
 *  i, abans que passi, tornar-ho a demanar no serviria de res).
 */
export default function ForgotPasswordView() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [resent, setResent] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = setTimeout(() => setSecondsLeft((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft]);

  async function request() {
    setBusy(true);
    setError(null);
    try {
      const { resend_cooldown_seconds } = await api.forgotPassword(email);
      // La resposta és la mateixa existeixi o no el compte: la pantalla tampoc ho ha de dir.
      setResent(sent);
      setSent(true);
      setSecondsLeft(resend_cooldown_seconds);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No s'ha pogut connectar amb l'API");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <div className="mx-auto max-w-sm px-4 py-10">
        <h2 className="mb-1 text-xl font-semibold text-slate-900">Reviseu el correu</h2>
        <p className="mb-3 text-sm text-slate-600">
          Si hi ha un compte amb l'adreça <strong className="break-words">{email}</strong>, us hem
          enviat un enllaç per triar una contrasenya nova. Caduca d'aquí a una hora.
        </p>
        <p className="mb-6 text-sm text-slate-500">
          Pot trigar un parell de minuts. Si no el veieu, mireu la carpeta de correu brossa.
        </p>

        <div role="status" aria-live="polite">
          {resent && (
            <p className="mb-4 rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700">
              Si l'adreça és correcta, rebreu un altre correu en uns instants. Si en vau demanar un
              fa poc, espereu una mica.
            </p>
          )}
        </div>
        {error && (
          <p role="alert" className="mb-4 rounded-md bg-brand-100 px-3 py-2 text-sm text-brand-700">
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={() => void request()}
          disabled={busy || secondsLeft > 0}
          className="w-full rounded-md bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50"
        >
          {secondsLeft > 0
            ? `Torna a enviar el correu (${secondsLeft} s)`
            : "Torna a enviar el correu"}
        </button>

        <p className="mt-6 text-center text-sm text-slate-500">
          <Link to="/login" className="font-medium text-brand-600 underline hover:text-brand-700">
            Torna a l'inici de sessió
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-10">
      <h2 className="mb-1 text-xl font-semibold text-slate-900">Heu oblidat la contrasenya?</h2>
      <p className="mb-6 text-sm text-slate-500">
        Escriviu el correu del compte i us enviarem un enllaç per triar-ne una de nova.
      </p>

      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          void request();
        }}
      >
        <Field label="Correu electrònic">
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className={INPUT}
          />
        </Field>

        {error && (
          <p role="alert" className="rounded-md bg-brand-100 px-3 py-2 text-sm text-brand-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50"
        >
          Envia l'enllaç
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        <Link to="/login" className="font-medium text-brand-600 underline hover:text-brand-700">
          Torna a l'inici de sessió
        </Link>
      </p>
    </div>
  );
}
