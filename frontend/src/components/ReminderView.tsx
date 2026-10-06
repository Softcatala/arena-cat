import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";

export default function ReminderView({ unsubscribe = false }: { unsubscribe?: boolean }) {
  const [params] = useSearchParams();
  const [frequency, setFrequency] = useState("never");
  const [loading, setLoading] = useState(!unsubscribe);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!unsubscribe) {
      api
        .reminders()
        .then((value) => {
          setFrequency(value.frequency);
          setLoading(false);
        })
        .catch(() => {
          setError(
            "No s'han pogut carregar les preferències. Recarregueu la pàgina per tornar-ho a provar.",
          );
        });
    }
  }, [unsubscribe]);
  async function save() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (unsubscribe) {
        await api.unsubscribeReminders(params.get("token") || "");
        setMessage("Ja no rebreu recordatoris.");
      } else {
        await api.saveReminders(frequency);
        setMessage("Preferències desades.");
      }
    } catch {
      setError("No s'ha pogut desar el canvi. Torneu-ho a provar.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="mx-auto max-w-xl space-y-4 px-4 py-10">
      <h2 className="text-xl font-bold">Recordatoris per correu</h2>
      {unsubscribe ? (
        <p>Podeu donar-vos de baixa dels recordatoris d'Arena Cat.</p>
      ) : (
        <>
          <p>
            Voleu rebre un recordatori quan faci dies que no voteu? Podeu canviar aquesta
            preferència en qualsevol moment. Després de tres recordatoris sense votar, pausarem els
            enviaments.
          </p>
          <label className="block">
            Freqüència
            <select
              className="ml-3 rounded border p-2"
              value={frequency}
              disabled={loading || busy}
              onChange={(event) => setFrequency(event.target.value)}
            >
              <option value="never">Mai</option>
              <option value="weekly">Setmanal</option>
              <option value="monthly">Mensual</option>
            </select>
          </label>
        </>
      )}
      <button
        className="rounded bg-brand-600 px-4 py-2 text-white disabled:opacity-50"
        disabled={loading || busy || (unsubscribe && (!params.get("token") || !!message))}
        onClick={() => void save()}
      >
        {busy ? "Desant…" : unsubscribe ? "Dona de baixa els recordatoris" : "Desa"}
      </button>
      {unsubscribe && !params.get("token") && (
        <p role="alert">L’enllaç de baixa és incomplet. Obriu l’enllaç del correu.</p>
      )}
      <p>
        <Link to="/" className="text-brand-600 underline">
          Torna a l’avaluació
        </Link>
      </p>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
