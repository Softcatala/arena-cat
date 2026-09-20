import { passwordChecks } from "../password";

/** Llista en viu dels requisits de la contrasenya nova: cada un es marca quan es compleix.
 *
 *  El símbol i el text van sempre junts, perquè el color sol no és prou (daltonisme), i el
 *  lector de pantalla llegeix l'estat. Es vincula al camp amb `aria-describedby` i no és
 *  una regió «live»: anunciar-la a cada lletra seria insuportable.
 */
export default function PasswordRules({ password, id }: { password: string; id: string }) {
  return (
    <ul id={id} className="-mt-2 space-y-0.5 text-xs">
      {passwordChecks(password).map((check) => (
        <li key={check.label} className={check.met ? "text-green-700" : "text-slate-500"}>
          <span aria-hidden="true">{check.met ? "✓" : "○"}</span> {check.label}
          <span className="sr-only">{check.met ? " (complert)" : " (pendent)"}</span>
        </li>
      ))}
    </ul>
  );
}
