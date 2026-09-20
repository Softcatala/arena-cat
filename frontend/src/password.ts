/** Política de les contrasenyes noves (alta i restabliment).
 *
 * És la mateixa que aplica el backend (`NewPassword` a `schemas.py`), que és qui
 * decideix: això només serveix per avisar mentre la persona escriu i abans d'enviar el
 * formulari. L'entrada no l'aplica, perquè un compte antic ha de poder entrar amb la
 * contrasenya que va triar.
 */

export const PASSWORD_MIN_LENGTH = 8;

// `[...password]` compta caràcters i no unitats UTF-16, com fa el backend.
const hasMinLength = (password: string) => [...password].length >= PASSWORD_MIN_LENGTH;
const hasCapital = (password: string) => /\p{Lu}/u.test(password);
const hasDigit = (password: string) => /\p{Nd}/u.test(password);

export interface PasswordCheck {
  label: string;
  met: boolean;
}

/** Cada requisit i si la contrasenya donada el compleix, per mostrar-los en viu. */
export function passwordChecks(password: string): PasswordCheck[] {
  return [
    { label: `Mínim ${PASSWORD_MIN_LENGTH} caràcters`, met: hasMinLength(password) },
    { label: "Una majúscula", met: hasCapital(password) },
    { label: "Un número", met: hasDigit(password) },
  ];
}

/** Missatge si la contrasenya no compleix la política, o `null` si és bona. */
export function passwordProblem(password: string): string | null {
  if (!hasMinLength(password)) {
    return `La contrasenya ha de tenir com a mínim ${PASSWORD_MIN_LENGTH} caràcters.`;
  }
  if (!hasCapital(password) || !hasDigit(password)) {
    return "La contrasenya ha de tenir almenys una majúscula i un número.";
  }
  return null;
}

/** Cert si la repetició ja s'ha desviat de la contrasenya. Mentre en sigui un prefix la
 *  persona encara està escrivint, i avisar-la a cada lletra només molestaria.
 */
export function repeatedDiverges(password: string, repeated: string): boolean {
  return repeated.length > 0 && !password.startsWith(repeated);
}
