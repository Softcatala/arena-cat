import { useState } from "react";

import { api, ApiError } from "../api";

type Mode = "login" | "register";

/** Entrada i alta. Són dos formularis diferents perquè demanen coses diferents:
 *  l'alta necessita confirmar la contrasenya i el consentiment, i l'entrada no.
 */
export default function Login({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeated, setRepeated] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isRegister = mode === "register";

  function switchTo(next: Mode) {
    setMode(next);
    setError(null);
    setRepeated("");
  }

  async function submit() {
    if (isRegister) {
      // El backend no té recuperació de contrasenya: una errada en teclejar-la
      // deixaria el compte inaccessible per sempre.
      if (password !== repeated) {
        setError("Les dues contrasenyes no coincideixen.");
        return;
      }
      if (!consent) {
        setError("Cal acceptar el tractament de dades per crear un compte.");
        return;
      }
    }

    setBusy(true);
    setError(null);
    try {
      // Amb REQUIRE_EMAIL_VERIFICATION=false el backend dona l'usuari per verificat,
      // així que després de l'alta ja es pot iniciar sessió.
      if (isRegister) await api.register(email, password, consent);
      await api.login(email, password);
      onLoggedIn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No s'ha pogut connectar amb l'API");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-10">
      <h2 className="mb-1 text-xl font-semibold text-slate-900">
        {isRegister ? "Crea un compte" : "Inicia la sessió"}
      </h2>
      <p className="mb-6 text-sm text-slate-500">
        Cal un compte per avaluar: així evitem vots duplicats i garantim la validesa del rànquing.
      </p>

      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
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

        <Field label="Contrasenya" hint={isRegister ? "Mínim 8 caràcters." : undefined}>
          <input
            type="password"
            required
            minLength={8}
            autoComplete={isRegister ? "new-password" : "current-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={INPUT}
          />
        </Field>

        {isRegister && (
          <>
            <Field label="Repeteix la contrasenya">
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={repeated}
                onChange={(event) => setRepeated(event.target.value)}
                className={INPUT}
              />
            </Field>

            {/* Consentiment explícit: el backend en desa la data i la versió a
                `users`, així que ha de reflectir un acte real de la persona. */}
            <label className="flex items-start gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={consent}
                onChange={(event) => setConsent(event.target.checked)}
                className="mt-0.5 h-4 w-4 shrink-0 accent-brand-500"
              />
              <span>Accepto el tractament de les meves dades per participar en l'avaluació.</span>
            </label>
          </>
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
          {isRegister ? "Crea el compte" : "Entra"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        {isRegister ? "Ja tens compte? " : "Encara no tens compte? "}
        <button
          type="button"
          onClick={() => switchTo(isRegister ? "login" : "register")}
          className="font-medium text-brand-600 underline hover:text-brand-700"
        >
          {isRegister ? "Inicia la sessió" : "Crea'n un"}
        </button>
      </p>
    </div>
  );
}

const INPUT =
  "w-full rounded-md border border-slate-300 px-3 py-2 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none";

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}
