import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api";

type State = "loading" | "success" | "invalid" | "failed";

/** Destinació de l'enllaç del correu de verificació: `/verify?token=…`. */
export default function VerifyView() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [state, setState] = useState<State>("loading");
  // Perquè «Torna-ho a provar» torni a executar l'efecte amb el mateix token.
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!token) {
      setState("invalid");
      return;
    }

    // En desenvolupament, StrictMode munta l'efecte dues vegades: la primera petició
    // es descarta i només compta l'última. El backend és idempotent, així que enviar-ne
    // dues no fa cap mal.
    let cancelled = false;
    setState("loading");
    api
      .verifyEmail(token)
      .then(() => {
        if (!cancelled) setState("success");
      })
      .catch((err) => {
        if (cancelled) return;
        // 400 i 404 volen dir que l'enllaç no serveix (caducat, manipulat o d'un compte
        // que ja no existeix); qualsevol altra cosa és un problema de connexió o del servei.
        const unusable = err instanceof ApiError && (err.status === 400 || err.status === 404);
        setState(unusable ? "invalid" : "failed");
      });
    return () => {
      cancelled = true;
    };
  }, [token, attempt]);

  return (
    <div className="mx-auto max-w-sm px-4 py-10 text-center">
      {state === "loading" && <p className="text-slate-500">Verificant el correu…</p>}

      {state === "success" && (
        <>
          <h2 className="mb-2 text-xl font-semibold text-slate-900">Correu verificat</h2>
          <p className="mb-6 text-sm text-slate-600">El compte ja està actiu. Ja pots entrar.</p>
          <Link to="/login" className={BUTTON}>
            Inicia la sessió
          </Link>
        </>
      )}

      {state === "invalid" && (
        <>
          <h2 className="mb-2 text-xl font-semibold text-slate-900">L'enllaç no és vàlid</h2>
          <p className="mb-6 text-sm text-slate-600">
            Pot haver caducat (duren 24 hores) o estar incomplet. Inicia la sessió i et podrem
            enviar un enllaç nou.
          </p>
          <Link to="/login" className={BUTTON}>
            Inicia la sessió
          </Link>
        </>
      )}

      {state === "failed" && (
        <>
          <p role="alert" className="mb-4 text-slate-600">
            No s'ha pogut verificar el correu ara mateix.
          </p>
          <button type="button" onClick={() => setAttempt((n) => n + 1)} className={BUTTON}>
            Torna-ho a provar
          </button>
        </>
      )}
    </div>
  );
}

const BUTTON =
  "block w-full rounded-md bg-brand-500 px-4 py-2 text-center font-medium text-white hover:bg-brand-600";
