import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { api, ApiError } from "../api";
import { downloadJson } from "../download";

interface Props {
  email: string | null;
  isAdmin: boolean;
  onLogout: () => void;
  onDeleteAccount: () => void;
}

const ITEM =
  "flex w-full items-center gap-2 px-4 py-2 text-left text-sm hover:bg-brand-100 focus-visible:bg-brand-100 focus-visible:outline-none";

/** Menú desplegable amb les accions del compte de la persona autenticada. */
export default function AccountMenu({ email, isAdmin, onLogout, onDeleteAccount }: Props) {
  const [open, setOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      button.current?.focus();
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  // Tanca el menú abans d'executar l'acció: alguna n'obre un diàleg i el menú no
  // hauria de quedar-se obert darrere.
  function run(action: () => void) {
    setOpen(false);
    action();
  }

  async function exportData() {
    setExporting(true);
    setExportError(null);
    try {
      const date = new Date().toISOString().slice(0, 10);
      downloadJson(await api.exportData(), `arena-cat-dades-${date}.json`);
      setOpen(false);
    } catch (err) {
      setExportError(
        err instanceof ApiError ? err.message : "No s'han pogut descarregar les dades.",
      );
    } finally {
      setExporting(false);
    }
  }

  return (
    <div
      ref={root}
      className="relative"
      onBlur={(event) => {
        // Tanca el desplegable quan el focus surt d'aquest bloc (per exemple amb Tab).
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <button
        ref={button}
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label="Menú del compte"
        title={email ?? "Compte"}
        className={`flex items-center gap-1 rounded-md p-2 hover:bg-brand-100 hover:text-brand-600 ${
          open ? "bg-brand-100 text-brand-600" : "text-slate-500"
        } focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none`}
      >
        <UserIcon />
        <ChevronIcon open={open} />
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-56 max-w-[calc(100vw-2rem)] rounded-md border border-slate-200 bg-white py-1 shadow-lg">
          <p className="border-b border-slate-200 px-4 py-2 text-sm break-all text-slate-500">
            {email}
          </p>
          <Link to="/reminders" onClick={() => setOpen(false)} className={`${ITEM} text-slate-700`}>
            <BellIcon />
            Recordatoris
          </Link>
          {isAdmin && (
            <Link to="/admin" onClick={() => setOpen(false)} className={`${ITEM} text-slate-700`}>
              <ShieldIcon />
              Administració
            </Link>
          )}
          <button
            type="button"
            onClick={() => void exportData()}
            disabled={exporting}
            className={`${ITEM} text-slate-700 disabled:text-slate-400`}
          >
            <DownloadIcon />
            {exporting ? "Descarregant…" : "Descarrega les meves dades"}
          </button>
          {exportError && (
            <p role="alert" className="px-4 pb-2 text-xs text-red-700">
              {exportError}
            </p>
          )}
          <div className="my-1 border-t border-slate-200" />
          <button
            type="button"
            onClick={() => run(onDeleteAccount)}
            className={`${ITEM} text-red-700`}
          >
            <TrashIcon />
            Dona de baixa el compte
          </button>
          <div className="my-1 border-t border-slate-200" />
          <button type="button" onClick={() => run(onLogout)} className={`${ITEM} text-slate-700`}>
            <LogoutIcon />
            Tanca la sessió
          </button>
        </div>
      )}
    </div>
  );
}

/** Icona d'un element del menú: mateix traç que la resta i mida fixa per alinear el text. */
function MenuIcon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4 shrink-0"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/** Porta amb una fletxa cap enfora: el gest habitual per a «surt». */
function LogoutIcon() {
  return (
    <MenuIcon>
      <path d="M9 21H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </MenuIcon>
  );
}

function BellIcon() {
  return (
    <MenuIcon>
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </MenuIcon>
  );
}

function DownloadIcon() {
  return (
    <MenuIcon>
      <path d="M12 3v12" />
      <path d="M7 10l5 5 5-5" />
      <path d="M5 21h14" />
    </MenuIcon>
  );
}

function ShieldIcon() {
  return (
    <MenuIcon>
      <path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6l8-3" />
      <path d="M9 12l2 2 4-4" />
    </MenuIcon>
  );
}

function TrashIcon() {
  return (
    <MenuIcon>
      <path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7" />
    </MenuIcon>
  );
}

function UserIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-5 w-5"
      aria-hidden="true"
    >
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </svg>
  );
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
      aria-hidden="true"
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}
