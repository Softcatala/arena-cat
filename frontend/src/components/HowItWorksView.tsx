import { useEffect } from "react";
import { Link } from "react-router-dom";

export default function HowItWorksView() {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <article className="mx-auto max-w-3xl px-4 py-8">
      <Link to="/" className="mb-4 inline-flex min-h-11 items-center text-brand-600 underline">
        Torna a l'inici
      </Link>
      <h2 className="mb-4 text-3xl font-bold">Com funciona l'Arena Cat?</h2>
      <p className="mb-8 leading-relaxed text-slate-600">
        Arena Cat és un projecte de Softcatalà per avaluar els models d'IA en català amb el criteri
        de la comunitat. La valoració humana ajuda a detectar errors i matisos que les puntuacions
        generals poden amagar.
      </p>

      <section className="mb-8">
        <h3 className="mb-3 text-xl font-semibold">Quins són els objectius?</h3>
        <ul className="list-disc space-y-3 pl-5 leading-relaxed text-slate-600">
          <li>
            <strong className="text-slate-900">Construir un rànquing públic.</strong> Saber quins
            models responen millor en català, globalment i per tipus de tasca.
          </li>
          <li>
            <strong className="text-slate-900">
              Publicar un conjunt de dades obert amb les preferències dels usuaris.
            </strong>{" "}
            Recollir les tasques, les respostes i les preferències perquè serveixin per entrenar i
            millorar models en català.
          </li>
        </ul>
      </section>

      <section className="mb-8">
        <h3 className="mb-3 text-xl font-semibold">Com podeu participar-hi?</h3>
        <ol className="list-decimal space-y-3 pl-5 leading-relaxed text-slate-600">
          <li>
            <strong className="text-slate-900">Creeu un compte</strong> amb el correu electrònic per
            desar el progrés i evitar vots duplicats.
          </li>
          <li>
            <strong className="text-slate-900">Supereu la prova de competència lingüística.</strong>{" "}
            Dura uns cinc minuts i només cal superar-la un cop. Si no la supereu, podeu repetir-la.
          </li>
          <li>
            <strong className="text-slate-900">Compareu i voteu.</strong> Llegiu l'enunciat i les
            respostes A i B a una mateixa tasca. Els noms dels models queden ocults per evitar
            biaixos de marca.
          </li>
        </ol>
        <p className="mt-3 leading-relaxed text-slate-600">
          No cal saber d'IA. Calculeu uns dos minuts per comparació i participeu al vostre ritme. El
          botó «Tutorial» de la pantalla d'avaluació us explica la interfície.
        </p>
      </section>

      <section className="mb-8">
        <h3 className="mb-3 text-xl font-semibold">Què heu de valorar?</h3>
        <p className="mb-4 leading-relaxed text-slate-600">
          Hi ha tasques de correcció, reformulació, traducció i generació. Seguiu els criteris de
          cada tasca: correcció i naturalitat del català, respecte del significat i compliment de
          les instruccions.
        </p>
        <dl className="space-y-3 leading-relaxed">
          <div>
            <dt className="font-semibold">A és millor / B és millor</dt>
            <dd className="text-slate-600">Una resposta resol millor la tasca.</dd>
          </div>
          <div>
            <dt className="font-semibold">Empat</dt>
            <dd className="text-slate-600">
              Tenen una qualitat semblant, sense una preferència clara.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">Cap de les dues</dt>
            <dd className="text-slate-600">Cap resposta resol la tasca de manera acceptable.</dd>
          </div>
          <div>
            <dt className="font-semibold">Omet</dt>
            <dd className="text-slate-600">
              Preferiu no valorar-la. No s'emet cap vot i la comparació no us tornarà a sortir.
            </dd>
          </div>
        </dl>
      </section>

      <section className="mb-8 rounded-lg border border-slate-200 bg-white p-5">
        <h3 className="mb-3 text-xl font-semibold">Un exemple de correcció</h3>
        <p className="mb-3 text-slate-600">
          Exemple inventat: cal corregir «Els nens juga al parc.»
        </p>
        <p className="mb-1">
          <strong>Resposta A:</strong> Els nens juguen al parc.
        </p>
        <p className="mb-3">
          <strong>Resposta B:</strong> Els nens juga al parc.
        </p>
        <p className="leading-relaxed text-slate-600">
          Triaríeu <strong>«A és millor»</strong>: «juguen» concorda amb «els nens». La resposta B
          manté l'error.
        </p>
      </section>

      <section className="mb-8">
        <h3 className="mb-3 text-xl font-semibold">Com s'interpreta el rànquing?</h3>
        <p className="mb-3 leading-relaxed text-slate-600">
          Les preferències A/B determinen les posicions; els empats i «Cap de les dues» es mostren
          per separat. Les puntuacions són relatives als models i les tasques avaluats.
        </p>
        <p className="leading-relaxed text-slate-600">
          La marca <strong>«Provisional»</strong> indica que encara no hi ha prou evidència per
          distingir un líder amb confiança. Les posicions poden canviar amb nous vots.
        </p>
      </section>

      <p className="mb-8 text-slate-600">
        Més informació a la{" "}
        <a
          href="https://github.com/Softcatala/arena-cat/blob/main/docs/projecte.md"
          className="text-brand-600 underline"
        >
          documentació del projecte
        </a>{" "}
        i al{" "}
        <a
          href="https://github.com/Softcatala/arena-cat#full-de-ruta"
          className="text-brand-600 underline"
        >
          full de ruta
        </a>
        .
      </p>

      <div className="rounded-lg border border-brand-200 bg-brand-100 p-6 text-center">
        <p className="mb-4 text-lg font-semibold text-brand-700">La vostra opinió compta</p>
        <Link
          to="/login"
          className="inline-flex min-h-11 items-center justify-center rounded-md bg-brand-500 px-5 py-2 font-semibold text-white hover:bg-brand-600 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:outline-none"
        >
          Vull participar-hi
        </Link>
      </div>
    </article>
  );
}
