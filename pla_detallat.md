# Pla detallat — Fita 1: Prova de concepte

> Aquest document detalla la **Part 1** de la [Fita 1](README.md#fita-1-prova-de-concepte): la construcció de la plataforma. Per a la motivació i la metodologia, vegeu [projecte.md](projecte.md). Per al resum executiu, vegeu el [full de ruta](README.md#full-de-ruta).

## Continguts

- [Estratègia de lliurament en tres versions](#estratègia-de-lliurament-en-tres-versions)

---

## Estratègia de lliurament en tres versions

Per arribar abans a un sistema utilitzable, dividim la construcció en tres entregues incrementals:

### v1 — *Nucli tècnic provable en local*

L'objectiu és tenir el bucle de votació funcionant tan aviat com sigui possible, sense compromisos d'integració externa.

- **30 *prompts* curats i revisats**:
    - Definició dels criteris que ha de complir cada *prompt*: avaluable (resposta clarament comparable), no ambigu, curt (llegible en 1-2 minuts amb les dues respostes), específic del català (que no es resolgui amb coneixement genèric en anglès), prou difícil perquè els models hi puguin discrepar, i amb varietat de dificultat i registre dins de cada categoria.
    - Redacció en YAML, 10 per categoria (correcció, reformulació, traducció).
    - Revisió creuada (lingüista + segon revisor).
    - Versionat a `data/prompts/v1/` al repositori.
- **Inferència executada i desada**:
    - *Script* `scripts/inferencia.py` que itera sobre les 90 combinacions (3 models × 30 *prompts*).
    - Sempre que sigui possible, **un únic motor d'inferència** per als 3 models — preferentment Hugging Face Transformers, que tot i no ser el més ràpid és la implementació de referència i la que minimitza el risc d'introduir variacions no atribuïbles al model.
    - Bolcat dels 90 JSONs a `data/inferencies/v1/`.
    - Metadades: `seed`, `quantization` i `model_version` per garantir reproduïbilitat.
- **Servidor SQL provisionat**:
    - PostgreSQL 16+ aixecat via `docker compose` amb volum persistent.
    - Creació de la base de dades `arena_cat` i del rol d'aplicació amb permisos limitats.
    - Variables d'entorn al `.env` (`DATABASE_URL`, credencials), amb `.env.example` versionat.
- **Model de dades**:
    - Taules `prompts`, `responses` i `votes` definides amb SQLAlchemy (sense `users` a v1).
    - Migracions amb Alembic per poder evolucionar l'esquema a v2.
    - Restriccions: `UNIQUE(prompt_id, model)` a `responses`, *enum* per `winner` (`a` | `b` | `tie` | `neither`).
    - Índexs sobre `votes.prompt_id` i `votes.created_at`.
- ***Script* de càrrega idempotent**:
    - `scripts/carrega_inferencies.py` que llegeix `data/prompts/v1/*.yaml` i `data/inferencies/v1/**/*.json`.
    - Pobla les taules `prompts` i `responses` amb *upsert* per clau primària.
    - Es pot tornar a executar sense duplicar files.
- **Servei web FastAPI**:
    - Esquelet `backend/app/`: `main.py`, `models.py` (SQLAlchemy), `schemas.py` (Pydantic), `db.py`, `routers/`.
    - Dependències a `pyproject.toml` (gestió amb uv o poetry): `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg`, `alembic`, `pydantic`, `pyyaml`.
    - CORS permissiu en mode desenvolupament perquè l'HTML local pugui cridar l'API.
    - Arrencada amb `uvicorn app.main:app --reload --port 8000`.
- **`GET /api/task`**:
    - Tria un *prompt* aleatori i dues respostes de models diferents per aquell *prompt*.
    - Aleatoritza l'ordre A/B per evitar biaix de posició.
    - Signa un `token_vot` HMAC que codifica els identificadors i un *timestamp*.
    - Retorna el *prompt*, les dues respostes i el *token*.
- **`POST /api/vote`**:
    - Verifica el `token_vot` (signatura i caducitat).
    - Valida el cos amb Pydantic (`winner ∈ {a, b, tie, neither}`).
    - Insereix una fila a `votes` amb `session_id` (extret d'una *cookie* anònima) i `response_time_s`.
    - *Rate limit* per `session_id`.
- **HTML local de proves** (`frontend/dev/index.html`):
    - Una sola pàgina amb HTML + JS petit, sense *framework*.
    - Crida `GET /api/task` i renderitza el *prompt* amb les dues respostes.
    - Quatre botons (A millor / B millor / empat / cap) que envien `POST /api/vote`.
    - Servida amb `python -m http.server` o oberta directament. No per a usuaris finals.
- **Proves**:
    - Tests unitaris dels dos *endpoints* amb `pytest` + `httpx.AsyncClient`.
    - Prova manual end-to-end: aixecar Postgres + FastAPI + l'HTML local i fer ~20 vots.
    - `README.md` del *backend* amb instruccions d'arrencada en local.

> **Per què v1 sense usuaris ni integració web**: permet validar la mecànica de votació, l'ergonomia bàsica i la qualitat dels *prompts* abans d'invertir esforç en autenticació, qualificació o integració amb tercers.

### v2 — *Plataforma completa amb usuaris*

- Registre i autenticació d'usuaris.
- Test de qualificació de 5 preguntes.
- *Endpoint* d'estadístiques (`GET /stats`) i pàgina pública de progrés.
- Lligam vot↔usuari per detectar abusos i ponderar contribucions.
- Indicador d'objectiu i progrés a la pàgina d'avaluació.

### v3 — *Integració amb la web de Softcatalà*

Un cop el sistema funciona end-to-end amb usuaris, es crea la **interfície definitiva integrable a la web de Softcatalà**, amb l'estil i el *layout* del lloc principal, llesta per obrir-se a la comunitat.

La integració es fa al repositori del WordPress de Softcatalà — [Softcatala/wp-softcatala](https://github.com/Softcatala/wp-softcatala) — escrivint **una plantilla PHP** que crida al **microservei FastAPI** d'Arena Cat. La plantilla viu dins del tema de WordPress; el *backend* d'Arena Cat es desplega com a microservei independent i la plantilla en consumeix els *endpoints* (`/api/task`, `/api/vote`, `/api/stats`, autenticació).

Softcatalà disposa de **maquinari propi** on es poden desplegar **contenidors Docker**, de manera que el microservei FastAPI d'Arena Cat es pot empaquetar i executar directament sobre aquesta infraestructura sense dependre de proveïdors externs. A més, Softcatalà manté un **GitLab intern que fa de mirall dels repositoris públics de GitHub**, cosa que permet integrar el desplegament del microservei amb el flux de CI/CD habitual de l'organització.

- Plantilla PHP nova al tema de [wp-softcatala](https://github.com/Softcatala/wp-softcatala) que renderitza la pàgina d'avaluació amb el *layout* habitual de softcatala.org (capçalera, peu, tipografia, colors).
- Crides al microservei: des del PHP (servidor a servidor) per al *render* inicial i des del navegador (JS lleuger) per a les accions interactives.
- Gestió d'autenticació coordinada entre WordPress i el microservei: opció A — Arena Cat manté el seu propi registre i el WP només l'embolcalla; opció B — *single sign-on* via el WordPress de Softcatalà. **Decisió pendent**, condiciona l'esquema d'usuaris de la v2.
- CORS, CSP i *cookie policy* d'acord amb les normes del lloc principal.
- Pàgines auxiliars dins de WordPress: presentació del projecte, instruccions per als avaluadors, FAQ.

