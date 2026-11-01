/** Client de l'API d'Arena Cat.
 *
 * Segueix el patró de Garbellaveus: una funció `request` genèrica i un objecte
 * `api` amb un mètode per endpoint.
 *
 * En desenvolupament, `BASE` és relatiu i Vite fa de proxy cap al backend local
 * (vegeu `vite.config.ts`). En producció s'hi posa l'URL del microservei via
 * `VITE_API_BASE_URL`.
 */

import { readDetail, readErrorCode, TASK_TOKEN_INVALID } from "./errors";
import type {
  Activity,
  AdminPrompt,
  AdminResponse,
  AdminUser,
  Category,
  CategoryFilter,
  ExportData,
  Progress,
  QualificationChoice,
  QualificationResult,
  Questionnaire,
  Ranking,
  ImportResult,
  Page,
  SessionState,
  Task,
  Winner,
} from "./types";

// `||` i no `??`: una variable definida però buida (cosa fàcil en un fitxer .env)
// ha de caure igualment al valor per defecte, o les crides perdrien el prefix /api.
const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

/** Error amb el codi HTTP, perquè la interfície pugui distingir 401 de 425 o 409. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** S'emet quan el backend rebutja la sessió, perquè la interfície hi reaccioni. */
export const UNAUTHENTICATED_EVENT = "arena-cat:unauthenticated";

async function request<T>(path: string, init?: RequestInit, notifyUnauthorized = true): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    // Imprescindible: la sessió viatja en una cookie HttpOnly que el backend
    // estableix a /auth/login. Sense això, /task i /vote responen 401.
    credentials: "include",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);

    // /vote i /task/skip també responen 401 quan el token de tasca (no la
    // sessió) ha caducat; el backend ho marca amb `error_code` perquè no ho
    // confonguem amb una sessió tancada i fem fora algú que encara hi és.
    if (
      notifyUnauthorized &&
      response.status === 401 &&
      readErrorCode(body) !== TASK_TOKEN_INVALID
    ) {
      window.dispatchEvent(new Event(UNAUTHENTICATED_EVENT));
    }

    const detail = readDetail(body);
    throw new ApiError(response.status, detail ?? `Error HTTP ${response.status}`);
  }

  // 204: l'esborrat d'administració no retorna cos.
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function query(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

const IMPORT_BATCH = 100;

const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

/** Endpoints d'administració (`/api/admin/*`): 403 si el compte no és administrador. */
const admin = {
  users: async (limit: number, offset: number): Promise<Page<AdminUser>> => {
    const data = await request<{ total: number; users: AdminUser[] }>(
      `/admin/users${query({ limit, offset })}`,
    );
    return { total: data.total, items: data.users };
  },
  blockUser: (id: number) => request<AdminUser>(`/admin/users/${id}/block`, { method: "POST" }),
  unblockUser: (id: number) => request<AdminUser>(`/admin/users/${id}/unblock`, { method: "POST" }),

  prompts: async (
    limit: number,
    offset: number,
    filters: { version?: string; category_code?: string; active?: boolean | "" },
  ): Promise<Page<AdminPrompt>> => {
    const data = await request<{ total: number; prompts: AdminPrompt[] }>(
      `/admin/prompts${query({ limit, offset, ...filters })}`,
    );
    return { total: data.total, items: data.prompts };
  },
  createPrompt: (prompt: { version: string; code: string; category_code: string; text: string }) =>
    request<AdminPrompt>("/admin/prompts", post(prompt)),
  updatePrompt: (id: number, changes: { active: boolean }) =>
    request<AdminPrompt>(`/admin/prompts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),
  deletePrompt: (id: number) => request<void>(`/admin/prompts/${id}`, { method: "DELETE" }),

  responses: async (
    limit: number,
    offset: number,
    filters: {
      prompt_id?: number | "";
      model?: string;
      active?: boolean | "";
      included_in_ranking?: boolean | "";
    },
  ): Promise<Page<AdminResponse>> => {
    const data = await request<{ total: number; responses: AdminResponse[] }>(
      `/admin/responses${query({ limit, offset, ...filters })}`,
    );
    return { total: data.total, items: data.responses };
  },
  /** Importa fitxers YAML de la canonada d'inferència; els envia per lots perquè el servidor en limita el nombre. */
  importResponses: async (
    version: string,
    files: { name: string; content: string }[],
  ): Promise<ImportResult> => {
    const total: ImportResult = { inserted: 0, skipped: 0, errors: 0, files: [] };
    for (let start = 0; start < files.length; start += IMPORT_BATCH) {
      const batch = await request<ImportResult>(
        "/admin/responses/import",
        post({ version, files: files.slice(start, start + IMPORT_BATCH) }),
      );
      total.inserted += batch.inserted;
      total.skipped += batch.skipped;
      total.errors += batch.errors;
      total.files.push(...batch.files);
    }
    return total;
  },
  createResponse: (response: { prompt_id: number; model: string; text: string }) =>
    request<AdminResponse>("/admin/responses", post(response)),
  updateResponse: (id: number, changes: { active?: boolean; included_in_ranking?: boolean }) =>
    request<AdminResponse>(`/admin/responses/${id}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),
  deleteResponse: (id: number) => request<void>(`/admin/responses/${id}`, { method: "DELETE" }),
};

export const api = {
  admin,
  reminderInvitation: () =>
    request<{ show: boolean }>("/auth/reminders/invitation", { method: "POST" }),
  reminders: () => request<{ enabled: boolean }>("/auth/reminders"),
  saveReminders: (enabled: boolean) =>
    request<{ enabled: boolean }>("/auth/reminders", {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    }),
  unsubscribeReminders: (token: string) =>
    request<{ status: string }>("/auth/reminders/unsubscribe", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  activity: (date: string) =>
    request<Activity>(date ? `/activity?date=${encodeURIComponent(date)}` : "/activity"),

  categories: async () => (await request<{ categories: Category[] }>("/categories")).categories,

  // Respon 200 tant si hi ha sessió com si no; la cookie és HttpOnly i el client
  // no té cap altra manera de saber-ho.
  session: () => request<SessionState>("/auth/session"),

  // `consent` ha de venir de la persona: el backend en desa la data i la versió a
  // `users`, i enviar-lo sempre cert fabricaria un consentiment que ningú ha donat.
  // La versió no s'envia: el backend la pren de la seva pròpia configuració.
  register: (email: string, password: string, consent: boolean) =>
    request<{ status: string; resend_cooldown_seconds?: number }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, consent }),
    }),

  login: (email: string, password: string) =>
    request<{ status: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),

  /** Dades personals, vots i omissions de la persona autenticada (RGPD). */
  exportData: () => request<ExportData>("/auth/export"),

  deleteAccount: async (password: string) => {
    try {
      return await request<{ status: string }>(
        "/auth/delete-account",
        { method: "POST", body: JSON.stringify({ current_password: password }) },
        false,
      );
    } catch (err) {
      // Una contrasenya incorrecta també retorna 401; comprovem la sessió abans de tancar-la.
      if (err instanceof ApiError && err.status === 401) {
        const session = await api.session();
        if (!session.authenticated) window.dispatchEvent(new Event(UNAUTHENTICATED_EVENT));
      }
      throw err;
    }
  },

  // El token és el de l'enllaç del correu. Verificar dues vegades no és cap error.
  verifyEmail: (token: string) =>
    request<{ status: string }>("/auth/verify", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  // Respon 200 amb el mateix cos tant si el correu existeix com si no, i també quan
  // encara cal esperar: així no revela quines adreces hi són ni si n'ha enviat cap.
  // `resend_cooldown_seconds` és l'espera configurada al backend, la mateixa per a tothom.
  resendVerification: (email: string) =>
    request<{ status: string; resend_cooldown_seconds: number }>("/auth/resend-verification", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  qualification: () => request<Questionnaire>("/qualification"),

  submitQualification: (answers: Record<string, QualificationChoice>, debug = false) =>
    request<QualificationResult>(debug ? "/qualification?debug" : "/qualification", {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),

  // Respon 200 amb el mateix cos tant si el correu existeix com si no, i també quan
  // encara cal esperar: així no revela quines adreces hi són ni si n'ha enviat cap.
  // `resend_cooldown_seconds` és l'espera configurada al backend, la mateixa per a tothom.
  forgotPassword: (email: string) =>
    request<{ status: string; resend_cooldown_seconds: number }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  // El token és el de l'enllaç del correu i només serveix un cop.
  resetPassword: (token: string, newPassword: string) =>
    request<{ status: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    }),

  // Sense `category_code` es prioritzen els prompts menys vistos entre totes les categories.
  nextTask: (category: CategoryFilter) =>
    request<Task>(category ? `/task?category_code=${encodeURIComponent(category)}` : "/task"),

  // Ometre és definitiu: el sampler exclou la cel·la omesa igual que una de votada.
  skipTask: (token: string) =>
    request<{ status: string }>("/task/skip", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  progress: () => request<Progress>("/task/progress"),

  // Públic: no cal sessió per veure el rànquing.
  ranking: (category: CategoryFilter) =>
    request<Ranking>(
      category ? `/ranking?category_code=${encodeURIComponent(category)}` : "/ranking",
    ),

  vote: (token: string, winner: Winner) =>
    request<{ status: string }>("/vote", {
      method: "POST",
      body: JSON.stringify({ token, winner }),
    }),
};
