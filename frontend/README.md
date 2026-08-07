# Interfície web d'Arena Cat

**React + TypeScript + Vite + Tailwind**, la mateixa pila que
[Garbellaveus](https://github.com/Softcatala/garbellaveus), amb els colors
corporatius de Softcatalà.

Cobreix el camí complet **inici de sessió → càrrega de tasca → vot**, amb el
progrés de l'avaluador, l'omissió de tasques i el ressaltat de diferències de la
categoria «correcció».

## Requisits

- **Node.js 20.19+ o 22.12+** (ho exigeix Vite 7). Comproveu-ho amb `node --version`.
- El backend en marxa i amb dades carregades. Des de l'arrel del repositori:

```bash
make setup
make run                        # o: docker compose up -d
make load_reference_inferences  # en una altra terminal
```

## Execució

```bash
cd frontend
npm ci        # `npm install` també val; `npm ci` respecta el package-lock
npm run dev
```

La interfície queda a <http://127.0.0.1:5173>.

> **No cal configurar el port.** El proxy llegeix l'`API_PORT` del `.env` de
> l'arrel del repositori, que és on es configura el backend; si no n'hi ha, fa
> servir el 8000. Canviar-lo en un sol lloc n'hi ha prou.
>
> Només cal `VITE_API_TARGET` si el backend és en una altra màquina:
>
> ```bash
> VITE_API_TARGET=http://192.168.1.50:8000 npm run dev
> ```

Vite fa de **proxy** de `/api` cap al backend (`vite.config.ts`). Això vol dir que el
navegador només veu un origen: no hi ha ni CORS ni el problema clàssic de barrejar
`127.0.0.1` amb `localhost`, que a la cookie de sessió li fan semblar dos llocs
diferents.

## Comprovacions

```bash
npm run typecheck     # tsc --noEmit
npm run format:check  # Prettier
npm run build         # compila a dist/
```

## Configuració

Totes les variables són a [`.env.example`](.env.example). Copieu-lo a `.env.local`
per a desenvolupament.

| Variable | Quan actua | Per a què |
|---|---|---|
| `VITE_API_TARGET` | `npm run dev` | Cap a on el proxy reenvia `/api`. Per defecte, `127.0.0.1` amb l'`API_PORT` del `.env` de l'arrel |
| `VITE_API_BASE_URL` | `npm run build` | URL base de l'API al lloc desplegat. Sense definir si el web i l'API comparteixen domini |

> **Vite incrusta les variables `VITE_*` dins del JavaScript en compilar.** No es
> poden canviar amb una variable d'entorn del servidor un cop fet el `build`: cal
> tornar a compilar. Si l'API canvia de domini, es recompila i es torna a desplegar.

## Desplegament

**Encara no està definit on ni com es publicarà.** El que sí que és cert:

- `npm run build` genera fitxers estàtics a `dist/`. No hi ha servidor de Node:
  els serveix qualsevol servidor web.
- És una aplicació d'una sola pàgina, o sigui que el servidor ha de retornar
  `index.html` per a qualsevol ruta que no correspongui a un fitxer.
- Si el servidor web publica el frontend i reenvia `/api` al backend sota el
  mateix origen, no cal definir cap variable: el client crida `/api`.
- Si l'API queda en un origen diferent, cal compilar amb `VITE_API_BASE_URL`, i
  el backend necessitarà una llista d'orígens permesos al CORS (ara hi ha
  `allow_origin_regex=".*"`, que no és acceptable de cara enfora) i
  `COOKIE_SECURE=true`.

Quan es concreti la infraestructura, aquest apartat s'ha d'omplir amb el que
s'hagi decidit.

## Estructura

| Fitxer | Contingut |
|---|---|
| `src/api.ts` | Client de l'API. `credentials: "include"` a totes les crides, imprescindible per la cookie de sessió. |
| `src/types.ts` | Tipus alineats amb `backend/app/schemas.py`. |
| `src/diff.ts` | Separa l'enunciat en instrucció i text, i calcula la diferència per paraules. És el que fa avaluable la categoria «correcció». |
| `src/taskStore.ts` | Conserva la tasca en curs entre recàrregues i llegeix el `vote_after` del token. |
| `src/errors.ts` | Tradueix al català els errors de validació de FastAPI, que arriben en anglès. |
| `src/App.tsx` | Estat de sessió i disposició general (capçalera i peu). |
| `src/components/Login.tsx` | Alta i inici de sessió. |
| `src/components/TaskView.tsx` | Filtre de categoria, tasca, vot, omissió i final de recorregut. |
| `src/components/ResponseCard.tsx` | Una resposta, amb ressaltat de canvis a «correcció». |
| `src/components/ProgressBar.tsx` | Progrés global de l'avaluador. |

## Detalls que no es poden ometre

- **L'espera de 10 segons abans de votar no és decorativa.** El backend signa a cada
  tasca un `vote_after` i rebutja amb **425** qualsevol vot anterior. La interfície
  ha de mantenir els botons bloquejats i explicar per què.
- **`GET /api/task` exigeix sessió.** Sense cookie vàlida retorna 401, així que no es
  pot maquetar la pantalla d'avaluació sense un inici de sessió funcional.
- **L'avaluació és cega.** El backend no envia mai quin model ha generat cada resposta.
  No cal (ni es pot) mostrar-ho.
- **Ometre una tasca és definitiu.** El sortejador exclou les cel·les omeses igual que
  les votades: no tornen a sortir mai més.
- **El 404 de `GET /api/task` no és un error.** Vol dir que no queda res per avaluar
  amb el filtre actual. Es distingeix «s'ha acabat la categoria» de «s'ha acabat tot»
  amb `GET /api/task/progress`.
- **El `consent` del registre ha de venir de la persona.** El backend en desa la data
  i la versió a `users`: enviar-lo sempre cert fabricaria un consentiment RGPD que
  ningú ha donat. La casella no és decorativa.

## Què falta

- **i18n** (`i18next` + `react-i18next`): Garbellaveus serveix català i anglès.
- **Encaminament** (`react-router-dom`): aquí tot passa en una sola pantalla.
- Pantalles de rànquing i estadístiques, i gestió del compte (exportació i baixa
  RGPD, que el backend ja implementa però no són accessibles des de la interfície).

### Endpoints que ajudarien

| Endpoint | Per a què |
|---|---|
| `GET /api/categories` | Ara les categories són a `src/types.ts`, escrites a mà. |
| Progrés per categoria | `GET /api/task/progress` només dona el total global. |
| `assess_confidence` al rànquing | Ja està implementat i provat al backend, però cap ruta el crida. |
