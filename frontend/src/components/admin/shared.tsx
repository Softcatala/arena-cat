import { ApiError } from "../../api";

export const PAGE_SIZE = 25;

/** Text d'error per mostrar a la persona, a partir de qualsevol excepció. */
export function messageOf(error: unknown): string {
  return error instanceof ApiError ? error.message : "No s'ha pogut connectar amb l'API.";
}

export function formatDate(iso: string | null): string {
  return iso
    ? new Date(iso).toLocaleString("ca-ES", { dateStyle: "short", timeStyle: "short" })
    : "—";
}

export function Badge({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "ok" | "warn" | "off";
}) {
  const colors = {
    ok: "bg-emerald-100 text-emerald-800",
    warn: "bg-amber-100 text-amber-800",
    off: "bg-slate-200 text-slate-700",
  };
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${colors[tone]}`}>
      {children}
    </span>
  );
}

/** Botó d'acció d'una fila; `danger` el tenyeix de vermell. */
export function ActionButton({
  children,
  onClick,
  disabled,
  danger,
  title,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
  title?: string;
}) {
  const tone = danger
    ? "border-red-300 text-red-700 hover:bg-red-50"
    : "border-slate-300 text-slate-700 hover:bg-slate-100";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`rounded-md border px-2 py-1 text-xs font-medium disabled:cursor-not-allowed disabled:opacity-40 ${tone}`}
    >
      {children}
    </button>
  );
}

/** Esborrat amb confirmació en dos passos, sense diàlegs del navegador. */
export function ConfirmDelete({
  onConfirm,
  disabled,
  title,
  confirming,
  setConfirming,
}: {
  onConfirm: () => void;
  disabled?: boolean;
  title?: string;
  confirming: boolean;
  setConfirming: (value: boolean) => void;
}) {
  if (!confirming) {
    return (
      <ActionButton danger disabled={disabled} title={title} onClick={() => setConfirming(true)}>
        Esborra
      </ActionButton>
    );
  }
  return (
    <span className="inline-flex gap-1">
      <ActionButton danger onClick={onConfirm}>
        Confirma
      </ActionButton>
      <ActionButton onClick={() => setConfirming(false)}>Cancel·la</ActionButton>
    </span>
  );
}

export function Pager({
  total,
  offset,
  onChange,
}: {
  total: number;
  offset: number;
  onChange: (offset: number) => void;
}) {
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);
  return (
    <div className="flex items-center justify-between text-sm text-slate-600">
      <span>
        {from}–{to} de {total.toLocaleString("ca-ES")}
      </span>
      <span className="flex gap-2">
        <ActionButton
          disabled={offset === 0}
          onClick={() => onChange(Math.max(0, offset - PAGE_SIZE))}
        >
          Anterior
        </ActionButton>
        <ActionButton
          disabled={offset + PAGE_SIZE >= total}
          onClick={() => onChange(offset + PAGE_SIZE)}
        >
          Següent
        </ActionButton>
      </span>
    </div>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  return message ? (
    <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
      {message}
    </p>
  ) : null;
}

export const TABLE = "w-full text-left text-sm";
export const TH = "px-3 py-2 font-medium text-slate-600";
export const TD = "px-3 py-2 align-top";
