import type { Progress } from "../types";

/** Concorda el nom amb la xifra que l'acompanya. */
function plural(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

/** Progrés global de l'avaluador (`GET /api/task/progress`), sumant totes les categories. */
export default function ProgressBar({
  progress,
  className = "",
}: {
  progress: Progress;
  className?: string;
}) {
  const { total, voted, skipped, remaining } = progress;
  const pct = (value: number) => (total > 0 ? (value / total) * 100 : 0);

  return (
    // `min-w-0` perquè, dins d'un flex, el text llarg no impedeixi encongir-se.
    <section className={`min-w-0 ${className}`}>
      {/* Al costat del desplegable hi ha poc ample: al mòbil escurcem el rètol en
          comptes de deixar que parteixi línia i es trepitgi amb el de la dreta. */}
      <div className="mb-1 flex items-baseline justify-between gap-2 text-sm whitespace-nowrap">
        <span className="font-medium text-slate-700">
          {voted} de {total}
          <span className="hidden sm:inline"> {total === 1 ? "avaluació" : "avaluacions"}</span>
        </span>
        <span className="text-slate-500">
          {skipped > 0 && (
            <span className="hidden sm:inline">{plural(skipped, "omesa", "omeses")} · </span>
          )}
          {plural(remaining, "pendent", "pendents")}
        </span>
      </div>

      <div
        className="flex h-2 overflow-hidden rounded-full bg-slate-200"
        role="progressbar"
        aria-valuenow={voted}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label="Avaluacions completades"
      >
        <div className="bg-brand-500" style={{ width: `${pct(voted)}%` }} />
        {/* Les omeses també consumeixen tasques, però no aporten dades al rànquing. */}
        <div className="bg-slate-400" style={{ width: `${pct(skipped)}%` }} />
      </div>
    </section>
  );
}
