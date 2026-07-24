# Client web d'Arena Cat

Client HTML mínim per provar l'API d'Arena Cat des del navegador: registre,
verificació de correu, inici de sessió, càrrega de tasques i votació.

- [index.html](index.html) — interfície (marcatge i estils).
- [app.js](app.js) — lògica: crides a l'API amb la cookie de sessió.

## Requisits previs

El backend ha d'estar en marxa i amb dades per servir tasques. Des de l'arrel
del repositori:

```bash
cp .env.example .env
docker compose up -d --wait
```

I, si encara no hi ha tasques, carrega'n de fictícies (des de `backend/`):

```bash
uv run python scripts/seed_mock_tasks.py
```

## Com fer-lo servir (amb `127.0.0.1`)

> **Important:** serveix la pàgina i crida l'API des del **mateix host**. La
> sessió es guarda en una cookie amb `SameSite=lax`, i el navegador només
> l'envia si l'origen de la pàgina i el de l'API es consideren el **mateix
> lloc** (*same-site*). `127.0.0.1` i `localhost` són llocs **diferents** per a
> les cookies: si els barreges, l'inici de sessió sembla funcionar però la
> càrrega de tasca retorna `401 Sessió invàlida o caducada`.

1. Serveix la carpeta `html/` amb un servidor estàtic a `127.0.0.1` (des de
   l'arrel del repositori):

   ```bash
   make http
   ```

2. Obre la pàgina al navegador:

   ```
   http://127.0.0.1:5500/index.html
   ```

3. Al camp **API**, posa-hi la mateixa família d'amfitrió que la pàgina:

   ```
   http://127.0.0.1:8000
   ```

   (Si en canvi obres la pàgina a `http://localhost:5500`, aleshores l'API ha
   de ser `http://localhost:8000`. No barregis `127.0.0.1` amb `localhost`.)

4. **Registra't**: introdueix email i contrasenya (mínim 8 caràcters), marca el
   consentiment i prem *Registra'm*.

5. **Verifica el correu**: a la v1 no hi ha servei de correu; el token de
   verificació s'escriu al log del backend. Recupera'l i enganxa'l al camp
   *Token de verificació*:

   ```bash
   docker logs arena-cat-api-1 2>&1 | grep "Email verification token"
   ```

   Prem *Verifica el correu*.

6. **Inicia sessió** amb el mateix email i contrasenya. La cookie de sessió es
   desa automàticament.

7. Prem **Carrega tasca** i vota. En votar, es carrega la tasca següent.

## Gestió del compte

Amb la sessió iniciada, la barra de sessió ofereix dues accions RGPD:

- **Exporta les meves dades**: descarrega un fitxer `arena-cat-dades.json` amb
  les teves dades de compte i tots els teus vots (`GET /api/auth/export`).
- **Dona de baixa el compte**: acció **irreversible** que anonimitza les teves
  dades personals i tanca la sessió (`POST /api/auth/delete-account`). Cal
  confirmar-la introduint la contrasenya actual; si és incorrecta, es manté la
  sessió oberta i pots reintentar-ho.

## Resolució de problemes

- **`401 Sessió invàlida o caducada` en carregar una tasca** (tot i haver
  iniciat sessió): el més probable és una barreja d'amfitrions. Assegura't que
  la pàgina i el camp **API** fan servir tots dos `127.0.0.1` (o tots dos
  `localhost`). Evita obrir la pàgina amb `file://` (origen nul, sempre
  *cross-site*).

- **La cookie no es desa sobre HTTP**: la cookie es marca com a `Secure`, cosa
  que el navegador tolera a `localhost` i `127.0.0.1` perquè es consideren
  contextos segurs. En qualsevol altre amfitrió (una IP de la xarxa local, un
  nom de domini...) sobre HTTP la cookie es descarta. Per a desenvolupament HTTP
  fora de `localhost`, posa `COOKIE_SECURE=false` al `.env` i recrea el servei:

  ```bash
  docker compose up -d --force-recreate api
  ```

- **`403` en iniciar sessió**: el compte existeix però el correu no està
  verificat. Completa el pas de verificació.

- **`404` en carregar una tasca**: no hi ha tasques disponibles per a la
  categoria (o ja les has votat totes). Carrega'n de fictícies amb
  `scripts/seed_mock_tasks.py`.
