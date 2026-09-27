import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import type { Activity } from "../types";

export default function ActivityView() {
  const [date, setDate] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [activity, setActivity] = useState<Activity | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setActivity(null);
    setError(false);
    api.activity(date).then(
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
  }, [date, refresh]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <Link to="/" className="text-sm text-brand-600 hover:underline">
        Torna a l'inici
      </Link>
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
            value={date || activity?.date || ""}
            onChange={(event) => setDate(event.target.value)}
            className="mt-1 block rounded-md border border-slate-300 bg-white px-3 py-2"
          />
        </label>
        <button
          type="button"
          onClick={() => {
            setDate("");
            setRefresh((value) => value + 1);
          }}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 hover:bg-slate-100"
        >
          Avui
        </button>
        <button
          type="button"
          onClick={() => setRefresh((value) => value + 1)}
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
              ["Usuaris registrats", activity.registered_users, "Comptes creats durant el dia."],
              [
                "Correus enviats",
                activity.verification_emails + activity.password_reset_emails,
                `${activity.verification_emails} de verificació i ${activity.password_reset_emails} de recuperació de contrasenya. Acceptats pel servidor de correu.`,
              ],
              [
                "Usuaris que han superat el test",
                activity.qualified_users,
                "Persones que s'han acreditat durant el dia.",
              ],
              [
                "Usuaris amb intents suspesos",
                activity.failed_users,
                "Persones amb almenys un suspens durant el dia, encara que després hagin aprovat.",
              ],
              [
                "Votants únics",
                activity.voters,
                "Persones que han emès almenys un vot durant el dia.",
              ],
              ["Vots emesos", activity.votes, "Inclou els empats i «cap de les dues»."],
            ].map(([label, value, description]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-white p-5">
                <dt className="font-medium text-slate-600">{label}</dt>
                <dd className="mt-2 text-3xl font-bold">{value.toLocaleString("ca-ES")}</dd>
                <dd className="mt-2 text-sm text-slate-500">{description}</dd>
              </div>
            ))}
          </dl>
          <p className="text-sm text-slate-500">
            Última actualització:{" "}
            {new Date(activity.updated_at).toLocaleString("ca-ES", { timeZone: "Europe/Madrid" })}.
          </p>
        </>
      )}
      <p className="text-sm text-slate-500">
        Els usuaris amb intents suspesos no inclouen els que encara no han fet el test. L'historial
        de correus i suspensos només està disponible des de l'activació d'aquests recomptes.
      </p>
    </div>
  );
}
