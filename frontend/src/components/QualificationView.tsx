import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api";
import type { Category, QualificationChoice, QualificationResult, Questionnaire } from "../types";

export default function QualificationView({
  categories,
  onContinue,
}: {
  categories: Category[];
  onContinue: () => Promise<void>;
}) {
  const [searchParams] = useSearchParams();
  const debug = searchParams.has("debug");
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null);
  const [answers, setAnswers] = useState<Record<string, QualificationChoice>>({});
  const [result, setResult] = useState<QualificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setQuestionnaire(await api.qualification());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No s'ha pogut carregar la prova.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (result) resultRef.current?.focus();
  }, [result]);

  function categoryName(code: string | null) {
    return code === null
      ? "Generals"
      : (categories.find((item) => item.code === code)?.name ?? code);
  }

  async function submit() {
    if (busy || result) return;
    setBusy(true);
    setError(null);
    try {
      const submission = await api.submitQualification(answers, debug);
      if (debug && submission.passed) {
        await onContinue();
      } else {
        setResult(submission);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No s'han pogut comprovar les respostes.");
    } finally {
      setBusy(false);
    }
  }

  if (!questionnaire) {
    return (
      <div className="px-4 py-10 text-center text-slate-500">
        {error ? (
          <>
            <p role="alert">{error}</p>
            <button type="button" onClick={() => void load()} className="mt-3 underline">
              Torna-ho a provar
            </button>
          </>
        ) : (
          <p>Carregant la prova…</p>
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h2 className="mb-2 text-2xl font-bold">Prova de competència lingüística</h2>
      {!result && (
        <>
          <p className="mb-4 text-slate-600">
            Per saber quins models d'IA responen millor en català, necessitem valoracions amb
            criteri lingüístic. Aquesta prova ens ajuda a comprovar que podeu identificar errors i
            valorar la qualitat de les respostes, perquè els resultats d'Arena Cat siguin fiables.
          </p>
          <p className="mb-4 text-slate-600">
            La prova dura aproximadament 5 minuts. Només cal superar-la un cop: no l'haureu de
            repetir quan torneu a iniciar sessió.
          </p>
          <p className="mb-6 text-slate-600">
            Abans de començar a avaluar, responeu aquestes {questionnaire.questions.length}{" "}
            preguntes. Trieu una resposta per pregunta: calen {questionnaire.min_correct} encerts
            per superar la prova. Podeu revisar les respostes abans d'enviar-les.
          </p>
        </>
      )}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
        className="space-y-6"
      >
        {!result &&
          questionnaire.questions.map((question, index) => (
            <fieldset
              key={question.id}
              disabled={busy}
              aria-describedby={`${question.id}-prompt`}
              className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5"
            >
              <legend className="px-1 font-semibold text-brand-600">
                {index + 1}. {categoryName(question.category_code)}
              </legend>
              <p id={`${question.id}-prompt`} className="mb-4 whitespace-pre-wrap">
                {question.prompt}
              </p>
              <div className="space-y-2">
                {(Object.keys(question.options) as QualificationChoice[]).map((choice) => (
                  <label
                    key={choice}
                    className="flex cursor-pointer items-start gap-3 rounded-md border border-slate-200 p-3 has-checked:border-brand-500 has-checked:bg-brand-50"
                  >
                    <input
                      type="radio"
                      name={question.id}
                      value={choice}
                      required={!debug}
                      checked={answers[question.id] === choice}
                      onChange={() =>
                        setAnswers((previous) => ({ ...previous, [question.id]: choice }))
                      }
                      className="mt-1 h-4 w-4 shrink-0 accent-brand-500"
                    />
                    <span>
                      <strong>{choice}.</strong> {question.options[choice]}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}

        {error && (
          <p role="alert" className="text-brand-700">
            {error}
          </p>
        )}

        {result ? (
          <div
            ref={resultRef}
            tabIndex={-1}
            role="status"
            className="rounded-lg border border-brand-100 bg-brand-50 p-5"
          >
            <h3 className="text-lg font-semibold">
              {result.passed ? "Heu superat la prova!" : "Encara no heu superat la prova."}
            </h3>
            <p className="mt-1 mb-4">
              {result.score} encerts de {result.total}. Calen {result.min_correct} encerts.
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                if (result.passed) {
                  setBusy(true);
                  void onContinue().finally(() => setBusy(false));
                } else {
                  setResult(null);
                  setAnswers({});
                  window.scrollTo({ top: 0 });
                }
              }}
              className="rounded-md bg-brand-500 px-5 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50"
            >
              {result.passed ? "Comença a avaluar" : "Torna-ho a provar"}
            </button>
          </div>
        ) : (
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-brand-500 px-5 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {busy ? "Comprovant…" : "Comprova les respostes"}
          </button>
        )}
      </form>
    </div>
  );
}
