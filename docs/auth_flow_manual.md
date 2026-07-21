# Flux d'autenticació — crides manuals a l'API

Aquest document llista les crides HTTP per recórrer el flux d'autenticació a mà
(amb `curl`), replicant el que fa `backend/scripts/auth_flow_demo.py`.

Assumeix el backend en marxa a `http://localhost:8000` (ajusta `BASE_URL` si cal).

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
{"status": "pending_verification"}
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

A la v1 **no hi ha servei de correu**: el token de verificació s'escriu al **log
del servidor**. Busca la línia:

```
Email verification token for demo@example.com: <TOKEN>
```

Copia'n el valor:

```bash
TOKEN='<enganxa-aquí-el-token-del-log>'
```

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

## 6. Obtenir una tasca

```bash
curl -s -b "$COOKIES" "$BASE_URL/api/task?category_code=correccio"
```

Resposta esperada (`200`):

```json
{
  "prompt": "…",
  "response_a": "…",
  "response_b": "…",
  "token": "<TASK_TOKEN>"
}
```

> Requereix dades sembrades (un prompt amb dues respostes). Si no n'hi ha,
> retorna `404`. Desa el token de la tasca per al vot:

```bash
TASK_TOKEN='<enganxa-aquí-el-token-de-la-tasca>'
```

---

## 7. Emetre un vot

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

## 8. Exportar les dades (RGPD)

```bash
curl -s -b "$COOKIES" "$BASE_URL/api/auth/export"
```

Resposta esperada (`200`): objecte amb `user` i la llista de `votes`.

---

## 9a. Logout (deixa el compte viu)

```bash
curl -s -b "$COOKIES" -X POST "$BASE_URL/api/auth/logout"
```

Resposta esperada (`200`):

```json
{"status": "logged_out"}
```

## 9b. Baixa del compte (anonimització RGPD)

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

## 10. (Control) La sessió ja no és vàlida → 401

Després del logout o la baixa, qualsevol crida autenticada ha de fallar:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -b "$COOKIES" "$BASE_URL/api/auth/export"
```

Resposta esperada: `401`.
