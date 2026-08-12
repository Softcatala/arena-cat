/** Conserva la tasca en curs entre recàrregues de la pàgina.
 *
 * `GET /api/task` tria una tasca nova a cada crida: sense això, actualitzar la
 * pàgina en descarta la que estaves llegint i en reinicia l'espera de 10 segons.
 *
 * El token de tasca és `base64url(json).signatura` — signat, no xifrat —, així
 * que en podem llegir la caducitat i el moment a partir del qual s'accepta el
 * vot. La signatura la continua validant només el backend.
 */

import type { Task } from "./types";

const KEY = "arena-cat.task";

interface TaskTokenPayload {
  /** Caducitat del token, en segons Unix. El backend la posa a una hora. */
  exp: number;
  /** Instant a partir del qual `/api/vote` deixa de respondre 425. */
  vote_after: number;
}

function decodeToken(token: string): TaskTokenPayload | null {
  try {
    const [payload] = token.split(".");
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const data: unknown = JSON.parse(atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "=")));

    if (typeof data !== "object" || data === null) return null;
    const { exp, vote_after: voteAfter } = data as Record<string, unknown>;
    if (typeof exp !== "number" || typeof voteAfter !== "number") return null;

    return { exp, vote_after: voteAfter };
  } catch {
    return null;
  }
}

/** Segons que falten perquè el backend accepti el vot. 0 si ja es pot votar. */
export function secondsUntilVote(token: string): number {
  const payload = decodeToken(token);
  if (!payload) return 0;
  return Math.max(0, Math.ceil(payload.vote_after - Date.now() / 1000));
}

export function saveTask(task: Task): void {
  sessionStorage.setItem(KEY, JSON.stringify(task));
}

export function clearTask(): void {
  sessionStorage.removeItem(KEY);
}

/** Recupera la tasca desada, o `null` si no n'hi ha o el token ja ha caducat. */
export function loadSavedTask(): Task | null {
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;

  try {
    const task = JSON.parse(raw) as Task;
    const payload = decodeToken(task.token);
    if (!payload || payload.exp <= Date.now() / 1000) {
      clearTask();
      return null;
    }
    return task;
  } catch {
    clearTask();
    return null;
  }
}
