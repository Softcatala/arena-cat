# Recordatoris per correu

Els recordatoris són opcionals i estan desactivats per defecte, també als comptes
existents. L'usuari els activa a **Recordatoris** de la capçalera (`/reminders`),
amb sessió iniciada. Després del primer vot, l'avaluació mostra un enllaç a
les preferències. La casella activa o desactiva el recordatori setmanal.
La tria es desa amb **Desa** i registra la data del consentiment quan s'activen
els recordatoris. El consentiment del registre no activa els recordatoris.

Només s'envia a comptes actius, amb correu verificat, acreditats, amb almenys
un vot i comparacions actives pendents. Cal que hagin passat 7 dies des
del més recent entre l'últim vot, el consentiment i l'últim recordatori.
Després de tres enviaments sense cap vot nou, els recordatoris es pausen;
un vot posterior permet reprendre'ls després del període d'inactivitat.
No s'envia cap recordatori a qui encara no ha votat.

Cada correu inclou el total històric de vots, un enllaç per avaluar, les
preferències i la baixa. La baixa no requereix sessió: l'enllaç obre una pantalla
amb un botó de confirmació, perquè els escàners de correu no provoquin baixes.
El token aleatori només permet desactivar recordatoris, no accedir al compte.
Tornar a activar els recordatoris renova el token; donar de baixa el compte l'elimina.
L'exportació personal inclou l'activació, la data del consentiment, l'últim
enviament i el comptador de recordatoris.

## API

- `GET /api/auth/reminders`: requereix sessió i retorna `{"enabled":false}` o `{"enabled":true}`.
- `PUT /api/auth/reminders`: requereix sessió i rep el mateix format.
- `POST /api/auth/reminders/unsubscribe`: rep `{"token":"…"}` sense sessió;
  retorna `{"status":"unsubscribed"}` també per a tokens desconeguts.

## Execució setmanal

Des de `backend/`, amb la configuració habitual de PostgreSQL i SMTP:

```bash
uv run python -m app.services.reminder_service
```

En una instal·lació amb Docker Compose, el planificador pot executar setmanalment (per exemple, cada dilluns a les 10 h):

```bash
docker compose exec -T api uv run python -m app.services.reminder_service
```

El desplegament ha de configurar aquesta execució al seu planificador; l'API
no inicia cap planificador intern. Sense `SMTP_HOST`, la comanda falla sense
enviar ni consumir recordatoris. Els errors SMTP tampoc consumeixen enviaments.
Els bloquejos de fila eviten que dos processos enviïn al mateix compte alhora.
SMTP i PostgreSQL no comparteixen transacció: si el procés cau després que SMTP
accepti el missatge i abans del commit, un reintent pot duplicar aquell correu.
El registre només acredita l'acceptació SMTP, no el lliurament a la bústia.
Els recordatoris no s'afegeixen als comptadors de verificació i recuperació
de contrasenya de la pàgina Activitat.
