/** Missatges d'error de l'API, en català.
 *
 * FastAPI fa servir el camp `detail` amb dues formes:
 *
 * - Errors de negoci: text ja en català, escrit al backend.
 *   `{"detail": "Aquest correu ja està registrat"}`
 * - Errors de validació: llista d'objectes de Pydantic, amb el missatge en
 *   anglès i el motiu codificat a `type`.
 *   `{"detail": [{"type": "string_too_short", "loc": ["body", "password"], …}]}`
 *
 * Els primers es mostren tal qual. Els segons els traduïm aquí a partir de
 * `type` i `loc`, que són estables, i no del text en anglès.
 *
 * Alguns errors hi afegeixen un camp `error_code` germà de `detail`, per
 * distingir-los sense dependre del text (vegeu `TASK_TOKEN_INVALID`).
 */

/** `error_code` que el backend posa als 401 del token de tasca (`/vote`,
 *  `/task/skip`), per distingir-los d'un 401 de sessió caducada: la sessió hi
 *  pot continuar sent vàlida encara que el token de la tasca no ho sigui.
 */
export const TASK_TOKEN_INVALID = "task_token_invalid";

interface ValidationItem {
  type: string;
  loc?: unknown[];
  msg?: string;
  ctx?: Record<string, unknown>;
}

/** Nom del camp tal com el veu la persona, no com es diu a l'esquema. */
const CAMPS: Record<string, string> = {
  email: "El correu electrònic",
  password: "La contrasenya",
  current_password: "La contrasenya actual",
  consent: "El consentiment",
  token: "El testimoni de la tasca",
  winner: "El vot",
  category_code: "La categoria",
};

function nomDelCamp(loc: unknown[] | undefined): string {
  // `loc` és ["body", "password"]: ens quedem amb l'últim tram que sigui text.
  const camp = loc?.filter((part): part is string => typeof part === "string").at(-1);
  return (camp && CAMPS[camp]) || "El valor";
}

function nombre(ctx: Record<string, unknown> | undefined, clau: string): number | null {
  const valor = ctx?.[clau];
  return typeof valor === "number" ? valor : null;
}

function tradueix(item: ValidationItem): string {
  const camp = nomDelCamp(item.loc);
  const esCorreu = item.loc?.includes("email") ?? false;

  switch (item.type) {
    case "missing":
      return `${camp} és obligatori.`;

    case "string_too_short": {
      const min = nombre(item.ctx, "min_length");
      return min === null
        ? `${camp} és massa curt.`
        : `${camp} ha de tenir com a mínim ${min} caràcters.`;
    }

    case "string_too_long": {
      const max = nombre(item.ctx, "max_length");
      return max === null
        ? `${camp} és massa llarg.`
        : `${camp} no pot superar els ${max} caràcters.`;
    }

    case "value_error":
      return esCorreu ? "El correu electrònic no és vàlid." : `${camp} no és vàlid.`;

    case "bool_parsing":
    case "bool_type":
      return `${camp} ha de ser cert o fals.`;

    case "string_type":
      return `${camp} ha de ser text.`;

    case "enum":
      return `${camp} té un valor no permès.`;

    default:
      // Tipus que no coneixem: val més el text original de Pydantic, encara que
      // sigui en anglès, que una frase vaga que amagui què ha passat.
      return item.msg ?? `${camp} no és vàlid.`;
  }
}

function esItemDeValidacio(valor: unknown): valor is ValidationItem {
  return (
    typeof valor === "object" &&
    valor !== null &&
    typeof (valor as { type?: unknown }).type === "string"
  );
}

/** Missatge llegible a partir del cos d'error, o `null` si no se'n pot treure cap. */
export function readDetail(body: unknown): string | null {
  if (typeof body !== "object" || body === null) return null;
  const { detail } = body as { detail?: unknown };

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const missatges = detail.filter(esItemDeValidacio).map(tradueix);
    if (missatges.length > 0) return missatges.join(" ");
  }

  return null;
}

/** `error_code` del cos d'error, o `null` si no n'hi ha cap. */
export function readErrorCode(body: unknown): string | null {
  if (typeof body !== "object" || body === null) return null;
  const { error_code: errorCode } = body as { error_code?: unknown };
  return typeof errorCode === "string" ? errorCode : null;
}
