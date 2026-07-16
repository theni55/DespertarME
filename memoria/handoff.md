# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

---

## Última sesión

**Fecha:** 2026-07-16 · **Sesión 12 — Fase 7a backend Device/FCM: código listo ✅. Pivot User/Twilio → Device/FCM ejecutado end-to-end.**

**Contexto:** tras cerrar el spike Android móvil (emulador + físico) en la Sesión 11, se arrancó la Fase 7a. El plan se cerró con el owner (3 bloques: limpieza bitácora, cierre spike en memorias, Fase 7a con 8 tandas) y se ejecutó sin contratiempos. 78 tests verdes, ruff/black/mypy limpios, migración Alembic en SQLite dev, server levanta con 9 endpoints.

**Logres de la sesión:**

- **Bloque 1 — Bitácora Sesión 11 limpiada**: la sección tenía escapes Unicode literales (`u00f3` como texto real, no como carácter) y caracteres de control (`\x07` BEL) que rompían legibilidad. Reescrito con texto limpio UTF-8.
- **Bloque 2 — Spike 100% cerrado en memoria**: `handoff.md` actualizado (móvil físico confirmó fix E1 + bypass DnD), `fases.md` checkboxes `Build EAS → móvil` y `Smoke OEM` marcados ✅, `decisiones.md` añadida **D42** (Home póster estático McGregor MVP + mejora post-MVP póster dinámico vía `image_url` en `EventSummaryOut`).
- **Bloque 3 — Fase 7a backend** (8 tandas):
  - **Tanda 0 (prep):** `Base.metadata.naming_convention` añadida, `app/common/ids.py` con `new_uuid()` mudado de `auth/dependencies.py`, imports migrados en 2 ficheros.
  - **Tanda 1 (deps+config):** `pyproject.toml` quita `passlib`, `bcrypt`, `pyjwt`, `twilio`, baja `pydantic[email]`→`pydantic`, añade `firebase-admin>=6.5`. `config.py` borra `jwt_*` (3), `twilio_*` (3) y `_check_production_secrets` juntos; añade `fcm_credentials_path`/`fcm_credentials_json`.
  - **Tanda 2 (borrado):** eliminados `auth/`, `notifiers/twilio.py`, `api/routes/auth.py` + `users.py`, `db/models/users.py`, `scripts/seed_admin.py`, `web/__pycache__/` (3 .pyc huérfanos), `SportSubscription` + `EventSubscription` del modelo (tablas muertas).
  - **Tanda 3 (migración Alembic a mano):** `alembic/versions/f7a0001_devices_fase_7a_*.py` (down_revision `a3657c6166f0`). Drop-and-recreate (destructivo: el pivot User→Device no tiene datos migrables). Crea `devices`, recrea `bout_subscriptions` (device_id FK, UNIQUE (device_id,bout_id), sin previous_bout_id) y `alert_log` (device_id, fired_at_epoch_hour). En PG dropea ENUMs `user_role`/`subscription_status`/`alert_status` explícito. Aplicada en SQLite dev: tablas y UNIQUE verificados.
  - **Tanda 4 (modelos+schemas):** `Device` model creado, `BoutSubscription`/`AlertLog` mutados, `schemas.py` reescrito (DeviceCreate/Out, BoutSubscriptionCreate sin previous_bout_id con `lead_minutes≥5`, BoutSubscriptionOut/AlertLogOut con device_id, EventSummaryOut con `image_url:None` D42, EventCardOut con previous_bout_id server-side).
  - **Tanda 5 (security+API):** `app/security/device.py` con `get_current_device` (header X-Device-Id estricto, 401/403). `api/routes/devices.py` (POST register/upsert, DELETE me, POST test-alarm). `api/routes/events.py` (GET con caché Redis 5 min, GET detalle con previous_bout_id E4). `main.py` con nuevo wiring devuelto a 5 routers.
  - **Tanda 6 (notifiers FCM):** `base.py` mutado (PushNotifier/PushResult/AlertPayload data-only con `type` update/started/cancelled/fire), `dummy.py` sin phone, `fcm.py` nuevo (firebase-admin data-only high-priority + asyncio.to_thread), `__init__.py` build_notifier gating + get_notifier singleton compartido por scheduler y test-alarm.
  - **Tanda 7 (engine bugfixes E2–E8):** `estimator.estimate` añade `observed_at` (E2). `state.py` añade `remember_transition/get_transition` (E2 anclaje in→post, TTL 24 h), `get_last_estimate/set_last_estimate` (D40 push on-change). `poller.py` reescrito: User→Device, E3 guard target (`in`→started, `post`→cancelled+mark fired), E4 previo derivado de card fresca, E2 observed_at pasado al estimador, E6 idempotencia tras éxito + `fired_at_epoch_hour`, E7 retries a `(2.0,)`, E8 agrupa subs por `event_id` con caché de Card, D40 push on-change con `MIN_DELTA_SECONDS=60`. `espn_ufc.py` E5 (`_on_failure` solo si `_is_retryable`) + `list_upcoming_events` filtra pasados por fecha + paraleliza con `asyncio.gather` limitado a 4. `scheduler.py` `misfire_grace_time=120` + `get_notifier()`.
  - **Tanda 8 (tests+lint+types):** `tests/conftest.py` añade scheduler/Firebase deshabilitado via env, `FakeNotifier` capturador, `FakeProvider` con `set_target_state/set_prev_state` independientes (E3), `make_device` helper. `tests/test_api.py` reescrito (15 tests con X-Device-Id, sin register/login/JWT). `tests/test_poller.py` reescrito (15 tests cubriendo E2/E3/E4/E6/E7 + D40 push on-change). `tests/test_notifiers.py` reescrito (8 tests FCM con firebase_admin mockeado + build_notifier gating). `tests/test_espn_ufc.py` añadido `test_e5_circuit_breaker_does_not_open_on_4xx` + ajustado `test_list_upcoming_events_returns_non_empty_list` (cutoff fijo). **Nuevo `tests/test_events_route.py`** (3 tests: lista image_url=None, detalle previous_bout_id server-side, 503 si provider cae). Total: **78 tests verdes** (54 preexistentes reescritos + 24 nuevos). ruff/black/mypy limpios.

**Pendientes externos (no bloquea Fase 7b):** Firebase project + service account key JSON + `google-services.json` para la app (manual del owner). Deploy Railway (cuenta del owner).

**Memorias actualizadas:** `handoff.md` (esta entrada), `bitacora.md` (Sesión 12), `fases.md` (Fase 7a completada con resumen ejecutivo), `decisiones.md` (D42). Commit + push a `dev` pendientes.

---

## Próximos pasos (ordenados para el continuador)

### Paso 1 — Fase 7b (app Android v1, D40/D41)

Ver checklist completo en `fases.md` §Fase 7b. El backend de Fase 7a está listo para consumir. Piezas nuevas:

1. `AlarmScheduler` con `AlarmManager.setAlarmClock()` programado a `estimated_start_at − lead` (D40). Verify-then-ring: al disparar, fetch `GET /api/events/{id}` (disponible ahora) → si target sigue `pre` y estimación < lead → arranca `AlarmService` (refactor del spike con sonido custom + `AlarmActivity` full-screen). Si ya empezó → notificación silenciosa. Si cancelado → reprogramar la alarma local.
2. Refactor `AlarmService` del spike: sonido custom embebido `res/raw/alarm.ogg` (en vez de `RingtoneManager.TYPE_ALARM` por defecto), `AlarmActivity` full-screen intent (`setShowWhenLocked`/`setTurnScreenOn`).
3. Cliente FCM: `@reactnative-firebase/messaging`. Handler background: `update` → `AlarmManager.setAlarmClock` (NO arrancar service). Handler foreground: `update` → actualizar UI; `started`/`cancelled` → notificación informativa. `google-services.json` en `mobile/android/app/`.
4. `expo-secure-store` para `device_id` (UUID v4 generado en 1ª launch).
5. Pantallas Expo Router Tabs: Home (hero + botón "Avísame" + "Eventos"), Eventos (desde `GET /api/events`), EventDetail (`GET /api/events/{id}`), Mis Alertas, Ajustes (con `POST /api/devices/me/test-alarm`), AlarmScreen modal.
6. Design tokens: Inter, rojo UFC `#E50914`, fondo oscuro `#0A0A0A` (reusados de la web D35/D36). Home usa `hero.webp` de McGregor estática (D42) hasta que ESPN proporcione `image_url`.

### Paso 2 — Firebase (manual del owner, paralelo a 7b)

1. Crear proyecto Firebase.
2. Service account key JSON (Python) → `FCM_CREDENTIALS_JSON` o path a un fichero.
3. `google-services.json` para la app Android (entra en `mobile/android/app/`).

### Paso 3 — Fase 7c (deploy + smoke real)

Backend en Railway con PG + Redis add-ons, `FCM_CREDENTIALS_JSON` env-var. Build EAS → APK. Smoke end-to-end: crear alerta → alarma local suena en hardware Android con DnD activo.

---

## Estado global

| Fase | Estado |
|------|--------|
| Fase 0 — Providers ESPN + tests | **Completada** ✅ |
| Fase 1 — Scaffold | **Completada** ✅ |
| Fase 2a — EstimatorEngine puro | **Completada** ✅ |
| Fase 2b — Poller + idempotencia | **Completada** ✅ |
| Fase 3 — Multiusuario + admin web | **Completada** ✅ |
| Fase MVP-launch — fotos + Twilio + scheduler + Railway | **Código listo** ✅ (deploy pendiente) |
| Fase 4 — Boxeo/Tenis reales | Pendiente (fuera del MVP) |
| Fase 5 — VoiceNotifier real (Twilio) | ❄️ **Obsoleta** — sustituida por FCM (D37/D40) |
| Fase 6 — Rediseño visual + landing dinámica | ❄️ **Congelada** — rama `web` |
| Fase 7 — App móvil | 🔶 **En curso** — Spike **100% cerrado** ✅ (emulador + móvil físico), **Fase 7a (backend Device/FCM) código listo** ✅, sesión sin Firebase real todavía. Próximo: Fase 7b (app Android con AlarmScheduler D40). |

Detalle de checkboxes en `fases.md`.

---

## Ramas

- `dev` (activa): backend API-only + `mobile/` spike + memoria viva. Commit + push de la Sesión 12 pendiente.
- `main`: sincronizada con `dev`.
- `web` (congelada en `dcf62f8`): landing, admin web, `/app/*`. `git checkout web` para consultarla.

---

## Cómo levantar el backend en local

```powershell
.\.venv\Scripts\Activate.ps1
# .env: DATABASE_URL=sqlite+aiosqlite:///./avisador.db
alembic upgrade head
uvicorn app.main:app --reload
```

- `http://localhost:8000/health` → `{"status":"ok"}`
- `http://localhost:8000/docs` → Swagger UI (9 endpoints: devices, events, subscriptions, alerts, health)

**La web solo existe en la rama `web`.**

---

## Comandos quick-start

```powershell
.\.venv\Scripts\Activate.ps1            # activar venv
alembic upgrade head                    # aplicar migraciones (SQLite dev)
uvicorn app.main:app --reload            # servidor dev (API-only)
pytest -v                                # tests (78 verdes en dev)
python scripts/probe_espn.py              # smoke ESPN en vivo
ruff check src tests                      # lint
black --check src tests scripts           # formato
mypy src/app                              # type check
python scripts/gen_memoria_index.py       # regenerar índice en AGENTS.md
```
