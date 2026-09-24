# Descripció del sistema

Arena Cat recull comparacions humanes entre respostes de models d'IA en català.
Les respostes es generen abans de l'avaluació i es carreguen a PostgreSQL.
Durant una votació, el servidor selecciona dues respostes desades: no executa
cap model en temps real.

La [motivació i la metodologia](projecte.md) expliquen què es vol mesurar.
Aquest document descriu els components, les dades i el funcionament de
l'aplicació. El [README](../README.md) conté l'arrencada ràpida.

## Arquitectura

```mermaid
flowchart LR
    P[Prompts i configuració] --> I[Generació d'inferències]
    I --> Y[Fitxers YAML]
    P --> L[Carregador]
    Y --> L
    L --> D[(PostgreSQL)]
    D <--> A[API FastAPI]
    A <--> F[Frontend React]
    D --> R[Rànquing i confiança]
    R --> A
```

| Component | Responsabilitat | Codi |
|---|---|---|
| Canonada d'inferència | Executa els models sobre els prompts i desa les respostes i les metadades | [`scripts/`](../scripts/README.md) |
| Carregador | Sincronitza categories i insereix prompts i respostes | [`carrega_inferencies.py`](../scripts/carrega_inferencies.py) |
| Backend | Autenticació, qualificació, tasques, vots, omissions, progrés i rànquing | [`backend/`](../backend/README.md) |
| Frontend | Interfície d'avaluació i consulta pública del rànquing | [`frontend/`](../frontend/README.md) |
| Base de dades | Persistència amb SQLAlchemy i migracions Alembic sobre PostgreSQL | [Esquema de dades](db_schema.md) |
| Simulador | Estimació del volum de comparacions i de l'esforç dels avaluadors | [`simulador/`](../simulador/) i [dimensionament](avaluadors.md) |

El frontend fa servir React, TypeScript, Vite i Tailwind. En desenvolupament,
Vite reenvia les peticions `/api` al backend, de manera que el navegador
treballa amb un sol origen. El backend exposa una API FastAPI amb validació
de peticions mitjançant Pydantic.

## Prompts i inferències

### Categories i models

El [catàleg de categories](../data/prompts/categories.yaml) defineix els noms,
les descripcions i els consells que veu l'avaluador. Les categories actuals són
generació, correcció, reformulació i traducció.

La [configuració d'inferència](../config/inferencia/inferencia_config.yaml)
defineix els models i les opcions d'execució. Actualment inclou:

| Model | Identificador del model d'origen |
|---|---|
| Qwen 3.8 27B | `Qwen/Qwen3.8-27B` |
| Mistral Small 3.2 24B Instruct | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` |
| Gemma 4 26B A4B Instruct | `google/gemma-4-26B-A4B-it` |

L'analitzador de prompts llegeix aquesta mateixa configuració per obtenir la
llista de models. Les opcions inclouen la revisió, el tipus numèric, la
quantització, els paràmetres de generació i la instrucció de sistema.
La canonada utilitza Transformers i també disposa d'un camí específic amb
`mistral_common` per al model Mistral configurat.

Els prompts han de permetre comparar les respostes amb criteri lingüístic:
instruccions clares, textos assumibles per a una lectura humana i varietat de
dificultat i registre. El seu format és text pla; la categoria es dedueix del
prefix del nom del fitxer.

### Generació i càrrega

Els fitxers segueixen aquesta estructura:

```text
data/prompts/<version>/<code>.txt
data/inferencies/<version>/<model_id>/<code>.yaml
```

[`inferencia.py`](../scripts/inferencia.py) llegeix els prompts i genera un
YAML per model i prompt. Hi desa la resposta, informació del model i de
l'execució, paràmetres de generació i un fingerprint per decidir si pot
reutilitzar un resultat existent. La seed registrada i les metadades ajuden
a identificar l'execució; no garanteixen per si soles una reproducció exacta.

[`carrega_inferencies.py`](../scripts/carrega_inferencies.py) importa aquests
fitxers a la base de dades. La càrrega és idempotent per `(version, code)` en
els prompts i per `(prompt_id, model)` en les respostes. Recarregar dades
idèntiques no crea duplicats. Els conflictes de text o de metadades de resposta
conservades es rebutgen; cal publicar una versió nova. El raonament intern,
quan n'hi ha, es desa a les metadades i no es mostra com a resposta.

Les inferències de referència es mantenen a la branca `dades_inferencia`.
Les comandes de generació, els filtres, les proves amb models petits i la
càrrega de dades es detallen a la [guia de la canonada](../scripts/README.md).

### Versions actives

`code` identifica un prompt concret, per exemple `traduccio_3`; `version`
identifica una revisió del seu text. Cada revisió té un `prompt_id` propi, al
qual apunten les respostes, els vots i les omissions.

Per a cada `code`, la versió activa és la més alta numèricament entre les que
tenen almenys dues respostes de models diferents. Les etiquetes tenen el format
`v<N>`, amb un enter positiu sense zeros inicials. Així, `v10` és posterior a
`v9`. No cal actualitzar tots els prompts alhora.

Si es carrega `traduccio_3/v2` amb una sola resposta, v1 continua activa. Quan
v2 té la segona resposta, substitueix v1 en les tasques, el progrés, el rànquing,
la confiança i el recompte de participants. Els vots de v1 es conserven com a
historial i a l'exportació personal, però no es traslladen a v2 ni compten en
els resultats vigents. Recarregar v1 no la reactiva.

La consulta comuna és a [`prompt_versions.py`](../backend/app/prompt_versions.py).
Si una tasca oberta correspon a una versió que ja no és activa, votar-la o
ometre-la retorna HTTP 410 i el frontend demana una altra tasca.

Per publicar o recarregar revisions, vegeu la
[guia de càrrega i versionatge](../scripts/README.md#8-carregar-prompts-i-inferències-a-la-base-de-dades).

## Recorregut de l'avaluador

1. La persona es registra amb correu, contrasenya i consentiment explícit.
2. Si `REQUIRE_EMAIL_VERIFICATION` està activat, verifica el correu mitjançant
   l'enllaç rebut abans d'iniciar sessió.
3. Supera la prova de competència lingüística. El
   [qüestionari](../data/qualification.yaml) actual té deu preguntes i exigeix
   vuit encerts. L'acreditació queda desada a `users.qualified_at`.
4. Rep un prompt i dues respostes anònimes, amb la possibilitat de filtrar per
   categoria. A correcció, pot veure les diferències respecte del text original.
5. Després de l'espera mínima de deu segons, vota A, B, empat o cap de les dues.
   També pot ometre la tasca. La interfície actualitza el progrés i en demana
   una altra.

La tasca en curs es conserva a `sessionStorage` per poder recuperar-la després
d'una recàrrega. En tancar la sessió es descarta. El frontend també ofereix
verificació del correu, recuperació de contrasenya, un tutorial i una pàgina
explicativa del projecte. La portada sense sessió mostra el rànquing públic.

Els detalls de les pantalles i del comportament del client són al
[README del frontend](../frontend/README.md).

### Selecció i registre de tasques

El selector considera cada combinació de prompt actiu i parella de models com
una cel·la. Dins de la categoria, tria aleatòriament entre les cel·les amb menys
vots i exclou les que l'usuari ja ha votat o omès. L'ordre de les respostes A/B
també és aleatori. Sense filtre de categoria, el servei recorre les categories
en ordre alfabètic fins a trobar feina pendent.

La justificació del mostreig es recull al
[disseny de selecció de tasques](ranking_design.md#4-selecció-de-tasques).

L'API no revela els noms dels models a la tasca i vincula cada vot a l'usuari
i les respostes amb un token signat. Les tasques, els vots, les omissions i el
progrés exigeixen sessió i qualificació. Els endpoints i els formats de les
peticions es descriuen a la [referència de l'API](../backend/README.md#api).

## Persistència i comptes

PostgreSQL conserva les categories, els prompts, les respostes, els comptes,
les sessions, els vots i les omissions. Les taules, les relacions, els índexs i
les restriccions estan descrits a l'[esquema de dades](db_schema.md).

El backend gestiona el registre, la verificació del correu, les sessions, la
recuperació de contrasenya, l'exportació i la baixa del compte. Els vots es
conserven quan un usuari es dona de baixa. La baixa i l'exportació estan
disponibles a l'API; el frontend encara no ofereix pantalles per a aquestes
operacions. Els fluxos, la criptografia, l'enviament de correu i la configuració
de seguretat es detallen a [gestió i autenticació d'usuaris](usuaris_autenticacio.md).

## Rànquing

El rànquing global o per categoria ajusta un model Bradley–Terry als vots
decisius de les versions actives. Els empats i els vots «cap de les dues» es
compten separadament. La resposta pública inclou les puntuacions i posicions
dels models, el nombre de vots i de participants i les mesures de confiança.

La confiança s'estima amb bootstrap agrupat per prompt. La interfície fa
servir el resultat d'estabilitat per indicar si el rànquing és provisional.
Quan la confiança no està disponible, mostra «Dades insuficients».
Els algoritmes són a [`backend/app/ranking/`](../backend/app/ranking/); el
[document de disseny estadístic](ranking_design.md) recull la justificació
i les limitacions, i el [dimensionament](avaluadors.md) estima l'esforç humà.

## Execució i desplegament

En local, [Docker Compose](../docker-compose.yml) aixeca PostgreSQL 16 i l'API.
El volum de PostgreSQL conserva les dades entre arrencades. La inicialització
crea un rol d'aplicació amb permisos limitats i una base de dades separada per
a les proves. Les migracions Alembic utilitzen el rol administrador.

La configuració es llegeix del `.env` de l'arrel i de les variables d'entorn;
[`.env.example`](../.env.example) en recull les opcions. Els targets `make` no
sobreescriuen un `.env` existent. En actualitzar una instal·lació, cal revisar
si falten variables; per exemple, si encara no hi ha `HMAC_SECRET_KEY`:

```bash
printf 'HMAC_SECRET_KEY=%s\n' "$(openssl rand -hex 32)" >> .env
```

El repositori defineix tres imatges:

- [`backend/Dockerfile`](../backend/Dockerfile): aplica les migracions i arrenca
  l'API amb Uvicorn al port 8000.
- [`frontend/Dockerfile`](../frontend/Dockerfile): compila el frontend i serveix
  els fitxers estàtics amb un servidor Node al port 80, amb retorn d'`index.html`
  per a les rutes de l'aplicació. `VITE_API_BASE_URL` es fixa en compilar.
- [`Dockerfile.load-inferences`](../Dockerfile.load-inferences): incorpora els
  prompts i les inferències v1 i executa el carregador.

La [configuració de GitLab CI](../.gitlab-ci.yml) construeix i publica aquestes
imatges i delega el desplegament al projecte d'infraestructura. Per construir
la imatge de càrrega, recupera les inferències de la branca `dades_inferencia`.

Per carregar les inferències precomputades en un entorn desplegat, amb el
fitxer de credencials `.env_loader` i la xarxa de PostgreSQL preparats:

```bash
docker run --rm --network arena-cat_arena_cat --env-file .env_loader \
  registry.softcatala.org/github/arena-cat/arena-cat-load-inferences:main
```

El nom de la xarxa i el fitxer d'entorn han de correspondre al desplegament.
La terminació HTTPS i les polítiques HTTP del proxy es configuren a la
infraestructura que publica el servei.

## Comprovacions

Els tests del backend utilitzen PostgreSQL amb transaccions aïllades per prova.
Cobreixen el model de dades, l'API, la càrrega, la selecció, el versionatge i
els càlculs del rànquing. Les proves de la canonada poden substituir els models
i tokenitzadors per dobles de prova, sense descarregar models grans.

Per provar el recorregut de registre, sessió, votació, exportació i baixa amb
crides a l'API, vegeu la [guia de proves manuals](auth_flow_manual.md).

[GitHub Actions](../.github/workflows/ci.yml) executa les migracions, els tests
i Ruff al backend, i la comprovació de tipus, el format i la compilació del
frontend. Les comandes locals són als README del
[backend](../backend/README.md), del [frontend](../frontend/README.md) i de la
[canonada](../scripts/README.md).
