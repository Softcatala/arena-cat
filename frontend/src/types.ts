/** Tipus compartits, alineats amb els esquemes Pydantic de `backend/app/schemas.py`. */

export type CategoryCode = "correccio" | "reformulacio" | "traduccio";

/** `""` vol dir «qualsevol»: `GET /api/task` sense `category_code` tria la primera pendent. */
export type CategoryFilter = CategoryCode | "";

export const CATEGORIES: { code: CategoryFilter; label: string }[] = [
  { code: "", label: "Qualsevol categoria" },
  { code: "correccio", label: "Correcció" },
  { code: "reformulacio", label: "Reformulació" },
  { code: "traduccio", label: "Traducció" },
];

/** El backend no revela mai quin model ha generat cada resposta: l'avaluació és cega. */
export interface Task {
  /** Categoria real de la tasca servida, que pot no coincidir amb la triada. */
  category_code: CategoryCode;
  prompt: string;
  response_a: string;
  response_b: string;
  token: string;
}

/** Estat d'autenticació segons `GET /api/auth/session`. */
export interface SessionState {
  authenticated: boolean;
  email: string | null;
  email_verified: boolean;
}

/** Progrés global de l'avaluador, en cel·les (prompt × parella de models). */
export interface Progress {
  total: number;
  voted: number;
  skipped: number;
  remaining: number;
}

export type Winner = "a" | "b" | "tie" | "neither";
