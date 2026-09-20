import { useEffect, useState } from "react";

import { api, ApiError } from "../api";

/** Pantalla d'«ha d'arribar-te un correu». Apareix després de l'alta i quan es
 *  vol entrar amb un compte encara sense verificar.
 *
 *  `justSent` és cert només després de l'alta, quan el correu acaba de sortir:
 *  llavors el reenviament comença bloquejat durant `cooldownSeconds`, l'espera que
 *  ha comunicat el backend (és configurable, i abans no serviria de res tornar-ho a
 *  demanar). Si la persona hi arriba en voler entrar, no sabem quan va sortir
 *  l'últim, així que el deixem disponible.
 */
export default function VerificationPending({
  email,
  justSent,
  cooldownSeconds,
  onBack,
}: {
  email: string;
  justSent: boolean;
  cooldownSeconds: number;
  onBack: () => void;
}) {
  const [secondsLeft, setSecondsLeft] = useState(justSent ? cooldownSeconds : 0);
  const [resent, setResent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = setTimeout(() => setSecondsLeft((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft]);

  async function resend() {
    setBusy(true);
    setError(null);
    try {
      const { resend_cooldown_seconds } = await api.resendVerification(email);
      setResent(true);
      setSecondsLeft(resend_cooldown_seconds);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No s'ha pogut connectar amb l'API");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-10">
      <h2 className="mb-1 text-xl font-semibold text-slate-900">
        {justSent ? "Revisa el correu" : "Verifica el correu"}
      </h2>
      <p className="mb-3 text-sm text-slate-600">
        {justSent ? "Hem enviat un enllaç de verificació a " : "Encara no has verificat "}
        <strong className="break-words">{email}</strong>
        {justSent
          ? ". Obre'l per activar el compte i després inicia la sessió."
          : ". Obre l'enllaç del correu que et vam enviar per activar el compte."}
      </p>
      <p className="mb-6 text-sm text-slate-500">
        Pot trigar un parell de minuts. Si no el veus, mira la carpeta de correu brossa.
      </p>

      {/* `role="status"` perquè un lector de pantalla anunciï el resultat sense
          haver de moure el focus. */}
      <div role="status" aria-live="polite">
        {resent && (
          <p className="mb-4 rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700">
            Si l'adreça és correcta, rebràs un altre correu en uns instants. Si en vas demanar un fa
            poc, espera una mica.
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
        onClick={() => void resend()}
        disabled={busy || secondsLeft > 0}
        className="w-full rounded-md bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50"
      >
        {secondsLeft > 0
          ? `Torna a enviar el correu (${secondsLeft} s)`
          : "Torna a enviar el correu"}
      </button>

      <p className="mt-6 text-center text-sm text-slate-500">
        <button
          type="button"
          onClick={onBack}
          className="font-medium text-brand-600 underline hover:text-brand-700"
        >
          Torna a l'inici de sessió
        </button>
      </p>
    </div>
  );
}
