# Flux d'autenticació — crides manuals a l'API

Aquest document llista les crides HTTP per recórrer el flux d'autenticació,
qualificació i votació a mà (amb `curl`).

Assumeix el backend en marxa a `http://localhost:8000` (ajusta `BASE_URL` si cal).
Per provar la verificació per correu dels passos 1–4, configura
`REQUIRE_EMAIL_VERIFICATION=true` al `.env` i reinicia el backend. Per treballar
en local amb HTTP, fes servir `COOKIE_SECURE=false`. Els exemples de cookies
assumeixen `COOKIE_NAME=session_token`.

Amb la configuració d'exemple (`REQUIRE_EMAIL_VERIFICATION=false`), el registre
retorna `{"status":"verified"}` i pots passar directament al pas 5.

```bash
BASE_URL=http://localhost:8000
EMAIL=demo@example.com
PASSWORD='Contrasenya-Segura-123'
COOKIES=cookies.txt        # fitxer on curl desa la cookie de sessió
```

> La cookie de sessió és `HttpOnly`; per mantenir-la entre crides fem servir el
> pot de galetes de curl (`-c` per desar-la, `-b` per enviar-la).

---

## 1. Registre

```bash
curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"consent\":true}"
```

Resposta esperada (`200`):

```json
{"status": "pending_verification", "resend_cooldown_seconds": 60}
```

---

## 2. (Control) Login abans de verificar → 403

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
```

Resposta esperada: `403` (email no verificat).

---

## 3. Obtenir el token de verificació

El registre envia un correu amb un enllaç del tipus
`<FRONTEND_BASE_URL>/verify?token=<TOKEN>`. El token és el valor del paràmetre `token`.

- **Amb SMTP configurat** (`SMTP_HOST` al `.env`): el correu arriba a la bústia de l'adreça
  registrada. Copia el token de l'enllaç.
- **Sense SMTP** (`SMTP_HOST` buit, el cas habitual en local): no s'envia res i el missatge
  sencer, enllaç inclòs, queda al **log del servidor**. Busca la línia:

```
SMTP no configurat; no s'envia el correu per a demo@example.com:
```

  i, a sota, l'enllaç `.../verify?token=<TOKEN>`.

Copia'n el valor:

```bash
TOKEN='<enganxa-aquí-el-token>'
```

Si el correu no arriba, es pot demanar un altre (com a màxim un cop cada
`VERIFICATION_RESEND_COOLDOWN_SECONDS`, 60 per defecte). La resposta és sempre la mateixa,
existeixi o no el compte:

```bash
curl -s -X POST "$BASE_URL/api/auth/resend-verification" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com"}'
```

Resposta esperada (`200`):

```json
{"status": "requested", "resend_cooldown_seconds": 60}
```

`resend_cooldown_seconds` és l'espera configurada; el frontend l'usa per al compte enrere del botó.

---

## 4. Verificació del correu

```bash
curl -s -X POST "$BASE_URL/api/auth/verify" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$TOKEN\"}"
```

Resposta esperada (`200`):

```json
{"status": "verified"}
```

---

## 5. Login (desa la cookie de sessió)

```bash
curl -s -c "$COOKIES" -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
```

Resposta esperada (`200`):

```json
{"status": "logged_in"}
```

La cookie `session_token` queda desada a `cookies.txt`.

---

## 6. Consultar l'estat de la sessió

```bash
curl -s -b "$COOKIES" "$BASE_URL/api/auth/session"
```

Resposta esperada (`200`):

```json
{"authenticated": true, "email": "demo@example.com", "email_verified": true, "qualified": false}
```

Sense cookie, o amb una de caducada o revocada, respon igualment `200`:

```json
{"authenticated": false, "email": null, "email_verified": false, "qualified": false}
```

> No tenir sessió és un estat normal, no un error: per això aquest endpoint no
> retorna mai `401`. Serveix perquè el client sàpiga si ha de demanar les
> credencials abans de fer cap altra crida.

---

## 6b. Superar la qualificació

Abans d'obtenir tasques o votar, cal superar la prova de competència:

```bash
curl -s -b "$COOKIES" "$BASE_URL/api/qualification"
```

La resposta conté `questions` i `min_correct`. Crea un fitxer `answers.json`
amb un objecte `answers` que associï **tots** els identificadors de pregunta
amb l'opció escollida (`"A"`, `"B"` o `"C"`), i envia'l:

```bash
curl -s -b "$COOKIES" -X POST "$BASE_URL/api/qualification" \
  -H "Content-Type: application/json" \
  --data-binary @answers.json
```

Exemple de resposta amb vuit encerts al qüestionari actual (`200`):

```json
{"score": 8, "total": 10, "min_correct": 8, "passed": true}
```

Si `passed` és `false`, cal repetir la prova. Un intent incomplet retorna `422`;
si ja l'has superada, un altre enviament retorna `409`. L'acreditació es conserva
entre sessions i `/api/auth/session` passa a indicar `qualified: true`.
Sense acreditar-te, les tasques, el progrés, els vots i les omissions retornen `403`.

---

## 7. Obtenir una tasca

```bash
curl -s -b "$COOKIES" "$BASE_URL/api/task?category_code=correccio"
```

Resposta esperada (`200`):

```json
{
  "category_code": "correccio",
  "prompt": "…",
  "response_a": "…",
  "response_b": "…",
  "token": "<TASK_TOKEN>"
}
```

> Requereix un prompt actiu amb dues respostes de models diferents. Si no hi ha
> tasques pendents a la categoria, retorna `404`. Només s'ofereixen les
> [versions actives](sistema.md#versions-actives). Desa el token de la tasca per al vot:

```bash
TASK_TOKEN='<enganxa-aquí-el-token-de-la-tasca>'
```

---

## 8. Consultar el progrés

```bash
curl -s -b "$COOKIES" "$BASE_URL/api/task/progress"
```

Exemple de resposta (`200`); els totals depenen de les dades actives carregades:

```json
{"total": 120, "voted": 0, "skipped": 0, "remaining": 120}
```

---

## 9. Emetre un vot

Cal esperar almenys deu segons des de l'obtenció de la tasca; si votes abans,
l'API retorna `425`. Les opcions són `a`, `b`, `tie` i `neither`.

```bash
curl -s -b "$COOKIES" -X POST "$BASE_URL/api/vote" \
  -H "Content-Type: application/json" \
  -d "{\"winner\":\"a\",\"token\":\"$TASK_TOKEN\"}"
```

Resposta esperada (`200`):

```json
{"status": "ok"}
```

---

## 10. Ometre una tasca

Si no vols votar la tasca carregada, pots ometre-la. Si ja has votat al pas 9,
demana una altra tasca al pas 7 i actualitza `TASK_TOKEN` abans de provar-ho:

```bash
curl -s -b "$COOKIES" -X POST "$BASE_URL/api/task/skip" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$TASK_TOKEN\"}"
```

Resposta esperada (`200`):

```json
{"status": "ok"}
```

La mateixa parella de respostes no es tornarà a oferir al mateix usuari.
Si una nova versió del prompt ha substituït la de la tasca oberta, tant el vot
com l'omissió retornen `410`: cal obtenir una tasca nova.

---

## 11. Exportar les dades (RGPD)

```bash
curl -s -b "$COOKIES" "$BASE_URL/api/auth/export"
```

Resposta esperada (`200`): objecte amb `user` i la llista de `votes`.

---

## 12a. Logout (deixa el compte viu)

```bash
curl -s -b "$COOKIES" -X POST "$BASE_URL/api/auth/logout"
```

Resposta esperada (`200`):

```json
{"status": "logged_out"}
```

## 12b. Baixa del compte (anonimització RGPD)

Alternativa al logout: dona de baixa el compte reautenticant amb la contrasenya.

```bash
curl -s -b "$COOKIES" -X POST "$BASE_URL/api/auth/delete-account" \
  -H "Content-Type: application/json" \
  -d "{\"current_password\":\"$PASSWORD\"}"
```

Resposta esperada (`200`):

```json
{"status": "deleted"}
```

---

## 13. (Control) La sessió ja no és vàlida → 401

Després del logout o la baixa, qualsevol crida autenticada ha de fallar:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -b "$COOKIES" "$BASE_URL/api/auth/export"
```

Resposta esperada: `401`.

---

## 14. (Opcional) Recuperar la contrasenya

Cal un compte que encara existeixi (no l'hagis donat de baixa al pas 12b). Es demana un
enllaç per triar una contrasenya nova; la resposta és sempre la mateixa, existeixi o no el
compte:

```bash
curl -s -X POST "$BASE_URL/api/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\"}"
```

Resposta esperada (`200`):

```json
{"status": "requested", "resend_cooldown_seconds": 60}
```

El correu porta l'enllaç `<FRONTEND_BASE_URL>/reset-password?token=<TOKEN>`. Sense SMTP
configurat, el missatge sencer queda al **log del servidor**. Copia'n el token i canvia la
contrasenya:

```bash
RESET_TOKEN='<enganxa-aquí-el-token>'
curl -s -X POST "$BASE_URL/api/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$RESET_TOKEN\",\"new_password\":\"NovaContrasenya456!\"}"
```

Resposta esperada (`200`):

```json
{"status": "password_reset"}
```

L'enllaç **només serveix un cop**: si repeteixes la petició, la resposta és `400`. Totes les
sessions del compte es tanquen, i cal iniciar sessió amb la contrasenya nova.
