import { useState } from "react";
import { Link } from "react-router-dom";

import { api, ApiError } from "../api";
import { PASSWORD_MIN_LENGTH, passwordProblem, repeatedDiverges } from "../password";
import { Field, INPUT } from "./Field";
import PasswordRules from "./PasswordRules";
import VerificationPending from "./VerificationPending";

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
  // Quan cal verificar el correu, la pantalla d'espera substitueix el formulari.
  const [pending, setPending] = useState<{
    email: string;
    justSent: boolean;
    cooldownSeconds: number;
  } | null>(null);

  const isRegister = mode === "register";

  function switchTo(next: Mode) {
    setMode(next);
    setError(null);
    setRepeated("");
  }

  async function submit() {
    if (isRegister) {
      // Es pot recuperar l'accés per correu, però una errada en teclejar la
      // contrasenya obligaria a fer-ho just després de crear el compte.
      const problem = passwordProblem(password);
      if (problem) {
        setError(problem);
        return;
      }
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
      if (isRegister) {
        const { status, resend_cooldown_seconds } = await api.register(email, password, consent);
        // Amb la verificació activada, el compte no deixa entrar fins que la persona
        // obri l'enllaç del correu: iniciar sessió ara només donaria un 403.
        if (status === "pending_verification") {
          setPending({ email, justSent: true, cooldownSeconds: resend_cooldown_seconds ?? 0 });
          return;
        }
      }
      await api.login(email, password);
      onLoggedIn();
    } catch (err) {
      // El backend només respon 403 a l'entrada quan la contrasenya és correcta però el
      // correu no està verificat.
      if (!isRegister && err instanceof ApiError && err.status === 403) {
        setPending({ email, justSent: false, cooldownSeconds: 0 });
        return;
      }
      setError(err instanceof ApiError ? err.message : "No s'ha pogut connectar amb l'API");
    } finally {
      setBusy(false);
    }
  }

  if (pending) {
    return (
      <VerificationPending
        email={pending.email}
        justSent={pending.justSent}
        cooldownSeconds={pending.cooldownSeconds}
        onBack={() => {
          setPending(null);
          setMode("login");
          setPassword("");
          setRepeated("");
          setConsent(false);
        }}
      />
    );
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-10">
      <h2 className="mb-1 text-xl font-semibold text-slate-900">
        {isRegister ? "Creeu un compte" : "Inicieu la sessió"}
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

        <Field label="Contrasenya">
          <input
            type="password"
            required
            // Només a l'alta: entrant, un compte antic pot tenir una contrasenya més curta.
            minLength={isRegister ? PASSWORD_MIN_LENGTH : undefined}
            aria-describedby={isRegister ? "password-rules" : undefined}
            autoComplete={isRegister ? "new-password" : "current-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={INPUT}
          />
        </Field>

        {isRegister && <PasswordRules id="password-rules" password={password} />}

        {!isRegister && (
          <p className="-mt-2 text-right text-sm">
            <Link to="/forgot-password" className="text-brand-600 underline hover:text-brand-700">
              Heu oblidat la contrasenya?
            </Link>
          </p>
        )}

        {isRegister && (
          <>
            <Field label="Repetiu la contrasenya">
              <input
                type="password"
                required
                minLength={PASSWORD_MIN_LENGTH}
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

            <p className="text-sm text-slate-600">
              Softcatalà és responsable del tractament de les vostres dades, amb el vostre
              consentiment, per gestionar el compte i les avaluacions i elaborar el rànquing de
              models. En donar-vos de baixa, s'eliminaran el correu i la contrasenya, però es
              conservaran els vots i les omissions de forma anònima. Consulteu els vostres drets a
              l'
              <a
                href="https://www.softcatala.org/avis-legal/"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-brand-700"
              >
                avís legal de Softcatalà
              </a>
              .
            </p>

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
        {isRegister ? "Ja teniu compte? " : "Encara no teniu compte? "}
        <button
          type="button"
          onClick={() => switchTo(isRegister ? "login" : "register")}
          className="font-medium text-brand-600 underline hover:text-brand-700"
        >
          {isRegister ? "Inicia la sessió" : "Crea'n un"}
        </button>
      </p>

      <hr className="my-6 border-slate-200" />

      <Link
        to="/"
        className="block w-full rounded-md border border-slate-300 px-4 py-2 text-center font-medium text-slate-700 hover:border-brand-500 hover:text-brand-600"
      >
        Consulta el rànquing
      </Link>
    </div>
  );
}
