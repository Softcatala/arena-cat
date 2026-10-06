import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import type { Activity } from "../types";

export default function ActivityView() {
  const [query, setQuery] = useState({ date: "" });
  const [activity, setActivity] = useState<Activity | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setActivity(null);
    setError(false);
    api.activity(query.date).then(
      (data) => {
        if (!cancelled) setActivity(data);
      },
      () => {
        if (!cancelled) setError(true);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [query]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <Link to="/" className="text-sm text-brand-600 hover:underline">
        Torna a l'inici
      </Link>
      <section aria-labelledby="global-counters" className="space-y-4">
        <div>
          <h2 id="global-counters" className="text-2xl font-bold">
            Comptadors globals
          </h2>
          <p className="mt-2 text-slate-600">
            Totals actuals de comptes que no s’han donat de baixa, independentment de la data
            seleccionada.
          </p>
        </div>
        {activity ? (
          <dl className="grid gap-4 sm:grid-cols-2">
            {[
              ["Usuaris registrats", activity.total_registered_users],
              ["Usuaris amb recordatoris activats", activity.reminder_subscribers],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-white p-5">
                <dt className="font-medium text-slate-600">{label}</dt>
                <dd className="mt-2 text-3xl font-bold">{value.toLocaleString("ca-ES")}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-slate-500">
            {error
              ? "No s’han pogut carregar els comptadors globals."
              : "Carregant comptadors globals…"}
          </p>
        )}
      </section>
      <div>
        <h2 className="text-2xl font-bold">Activitat</h2>
        <p className="mt-2 text-slate-600">
          Activitat diària de tota la plataforma. El dia es compta de mitjanit a mitjanit, segons
          l'hora d'Europa/Madrid.
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm font-medium">
          Data
          <input
            type="date"
            value={query.date || activity?.date || ""}
            onChange={(event) => setQuery({ date: event.target.value })}
            className="mt-1 block rounded-md border border-slate-300 bg-white px-3 py-2"
          />
        </label>
        <button
          type="button"
          onClick={() => setQuery({ date: "" })}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 hover:bg-slate-100"
        >
          Avui
        </button>
        <button
          type="button"
          onClick={() => setQuery({ ...query })}
          className="rounded-md bg-brand-500 px-4 py-2 text-white hover:bg-brand-600"
        >
          Actualitza
        </button>
      </div>
      {error ? (
        <p role="alert" className="text-red-700">
          No s'ha pogut carregar l'activitat. Torneu-ho a provar amb el botó «Actualitza».
        </p>
      ) : !activity ? (
        <p role="status" className="text-slate-500">
          Carregant activitat…
        </p>
      ) : (
        <>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              ["Usuaris registrats", activity.registered_users],
              [
                "Correus enviats de registre",
                activity.verification_emails + activity.password_reset_emails,
              ],
              ["Correus de recordatori enviats", activity.reminder_emails],
              ["Usuaris que han superat el test", activity.qualified_users],
              ["Usuaris amb prova suspesa", activity.failed_users],
              ["Votants únics", activity.voters],
              ["Vots emesos", activity.votes],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-white p-5">
                <dt className="font-medium text-slate-600">{label}</dt>
                <dd className="mt-2 text-3xl font-bold">{value.toLocaleString("ca-ES")}</dd>
              </div>
            ))}
          </dl>
          <p className="text-sm text-slate-500">
            Últims enviaments desats als comptes: {activity.verification_emails} de verificació,{" "}
            {activity.password_reset_emails} de recuperació de contrasenya i{" "}
            {activity.reminder_emails} de recordatori.
          </p>
          <p className="text-sm text-slate-500">
            Última actualització:{" "}
            {new Date(activity.updated_at).toLocaleString("ca-ES", { timeZone: "Europe/Madrid" })}.
          </p>
        </>
      )}
      <p className="text-sm text-slate-500">
        Els recomptes d’usuaris i votants compten cada persona una vegada. Pot haver suspès i
        aprovat el mateix dia; qui encara no ha fet el test no compta com a suspès. Els vots
        inclouen els empats i «cap de les dues». Els correus compten l’última data desada per compte
        i tipus; nous enviaments poden modificar els recomptes de dies anteriors. Les dates de
        verificació i recuperació es desen abans de contactar amb SMTP i poden incloure intents
        fallits. L’historial de suspensos només està disponible des de l’activació del seu registre.
      </p>
    </div>
  );
}
