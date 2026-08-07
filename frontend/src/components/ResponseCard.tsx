import { diffWords } from "../diff";

interface Props {
  label: string;
  text: string;
  /** Text d'origen per al diff. Només s'hi passa a "correcció". */
  source?: string;
}

/** Mostra una resposta. A "correcció" en ressalta les diferències amb l'original. */
export default function ResponseCard({ label, text, source }: Props) {
  return (
    <article className="flex flex-col rounded-lg border border-slate-200 bg-white shadow-sm">
      <h3 className="border-b border-slate-200 px-4 py-2 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        {label}
      </h3>
      <div className="flex-1 px-4 py-3 leading-relaxed whitespace-pre-wrap text-slate-800">
        {source ? <DiffText source={source} text={text} /> : text}
      </div>
    </article>
  );
}

function DiffText({ source, text }: { source: string; text: string }) {
  const changes = diffWords(source, text);

  return (
    <p>
      {changes.map((change, index) => (
        <span key={index}>
          {index > 0 && " "}
          {change.type === "added" ? (
            <ins className="rounded bg-emerald-100 px-0.5 text-emerald-900 no-underline">
              {change.text}
            </ins>
          ) : change.type === "removed" ? (
            <del className="rounded bg-brand-100 px-0.5 text-brand-700">{change.text}</del>
          ) : (
            change.text
          )}
        </span>
      ))}
    </p>
  );
}
