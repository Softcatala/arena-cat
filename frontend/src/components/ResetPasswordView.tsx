import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api";
import { PASSWORD_MIN_LENGTH, passwordProblem, repeatedDiverges } from "../password";
import { Field, INPUT } from "./Field";
import PasswordRules from "./PasswordRules";

/** Destinació de l'enllaç del correu de restabliment: `/reset-password?token=…`. */
export default function ResetPasswordView() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [password, setPassword] = useState("");
  const [repeated, setRepeated] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  // 400: l'enllaç no serveix (caducat, ja utilitzat o manipulat).
  const [invalid, setInvalid] = useState(!token);

  async function submit() {
    if (!token) return;
    const problem = passwordProblem(password);
    if (problem) {
      setError(problem);
      return;
    }
    if (password !== repeated) {
      setError("Les dues contrasenyes no coincideixen.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setInvalid(true);
      } else {
        setError(err instanceof ApiError ? err.message : "No s'ha pogut connectar amb l'API");
      }
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="mx-auto max-w-sm px-4 py-10 text-center">
        <h2 className="mb-2 text-xl font-semibold text-slate-900">Contrasenya canviada</h2>
        <p className="mb-6 text-sm text-slate-600">
          Ja podeu entrar amb la contrasenya nova. Les sessions obertes s'han tancat.
        </p>
        <Link to="/login" className={BUTTON}>
          Inicia la sessió
        </Link>
      </div>
    );
  }

  if (invalid) {
    return (
      <div className="mx-auto max-w-sm px-4 py-10 text-center">
        <h2 className="mb-2 text-xl font-semibold text-slate-900">L'enllaç no és vàlid</h2>
        <p className="mb-6 text-sm text-slate-600">
          Pot haver caducat (duren una hora), ja s'ha fet servir o estar incomplet. Demaneu-ne un de
          nou.
        </p>
        <Link to="/forgot-password" className={BUTTON}>
          Demana un enllaç nou
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-10">
      <h2 className="mb-1 text-xl font-semibold text-slate-900">Trieu una contrasenya nova</h2>
      <p className="mb-6 text-sm text-slate-500">
        Escriviu-la dues vegades perquè no hi hagi cap errada.
      </p>

      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <Field label="Contrasenya nova">
          <input
            type="password"
            required
            minLength={PASSWORD_MIN_LENGTH}
            maxLength={128}
            aria-describedby="password-rules"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={INPUT}
          />
        </Field>

        <PasswordRules id="password-rules" password={password} />

        <Field label="Repetiu la contrasenya">
          <input
            type="password"
            required
            minLength={PASSWORD_MIN_LENGTH}
            maxLength={128}
            autoComplete="new-password"
            value={repeated}
            onChange={(event) => setRepeated(event.target.value)}
            className={INPUT}
          />
        </Field>

        {repeatedDiverges(password, repeated) && (
          <p role="status" className="-mt-2 text-xs text-brand-700">
            Les dues contrasenyes no coincideixen.
          </p>
        )}

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
          Canvia la contrasenya
        </button>
      </form>
    </div>
  );
}

const BUTTON =
  "block w-full rounded-md bg-brand-500 px-4 py-2 text-center font-medium text-white hover:bg-brand-600";
