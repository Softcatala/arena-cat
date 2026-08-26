import { useLayoutEffect, useState, type RefObject } from "react";

export interface OnboardingStep {
  ref: RefObject<HTMLElement | null>;
  title: string;
  text: string;
}

const TOOLTIP_WIDTH = 288;
const GAP = 12;

/** Tutorial de primer ús: assenyala, un per un, els blocs clau de la pantalla d'avaluació. */
export default function Onboarding({
  steps,
  onDone,
}: {
  steps: OnboardingStep[];
  onDone: () => void;
}) {
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const step = steps[index];

  useLayoutEffect(() => {
    const target = step.ref.current;
    if (!target) return;

    target.scrollIntoView({ block: "center", behavior: "smooth" });

    const update = () => setRect(target.getBoundingClientRect());
    update();
    // El `scrollIntoView` és animat: recalculem un cop acabat perquè el
    // requadre no quedi assenyalant la posició d'abans de l'scroll.
    const afterScroll = setTimeout(update, 350);
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      clearTimeout(afterScroll);
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [step]);

  function next() {
    if (index === steps.length - 1) onDone();
    else setIndex(index + 1);
  }

  if (!rect) return null;

  const pad = 8;
  const spaceBelow = window.innerHeight - rect.bottom;
  const tooltipTop =
    spaceBelow > 200 ? rect.bottom + pad + GAP : Math.max(GAP, rect.top - pad - GAP - 180);
  const tooltipLeft = Math.min(Math.max(GAP, rect.left), window.innerWidth - TOOLTIP_WIDTH - GAP);

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Tutorial">
      <div
        className="pointer-events-none absolute rounded-lg transition-all duration-300"
        style={{
          top: rect.top - pad,
          left: rect.left - pad,
          width: rect.width + pad * 2,
          height: rect.height + pad * 2,
          boxShadow: "0 0 0 9999px rgba(15, 23, 42, 0.65)",
        }}
      />
      <div
        className="absolute rounded-lg bg-white p-4 shadow-xl transition-all duration-300"
        style={{ top: tooltipTop, left: tooltipLeft, width: TOOLTIP_WIDTH }}
      >
        <p className="mb-1 text-xs font-semibold tracking-wide text-brand-600 uppercase">
          Pas {index + 1} de {steps.length}
        </p>
        <h3 className="mb-1 font-semibold text-slate-900">{step.title}</h3>
        <p className="mb-3 text-sm text-slate-600">{step.text}</p>
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={onDone}
            className="text-sm text-slate-500 underline hover:text-slate-700"
          >
            Omet el tutorial
          </button>
          <button
            type="button"
            onClick={next}
            className="rounded-md bg-brand-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-600"
          >
            {index === steps.length - 1 ? "Entesos" : "Següent"}
          </button>
        </div>
      </div>
    </div>
  );
}
