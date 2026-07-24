# Fases de implementación

> Roadmap por fases con checkboxes. Marca los sub-items al completarlos y refleja el avance en handoff.md.

## Fase 0 — Providers ESPN UFC + tests ✅ (completada en Sesión 4)

- [x] Interfaz `Provider` (`base.py`) con `list_upcoming_events`, `get_event_card`, `get_competition_status`
- [x] Implementación `espn_ufc.py` con httpx async + backoff exponencial con jitter (D20) + circuit breaker (D20)
- [x] **Fixtures JSON grabadas** en `tests/fixtures/espn_ufc/`: event_list.json, event_600059148.json, competition_status_pre.json, competition_status_in.json, competition_status_post.json
- [x] Tests unitarios en `tests/test_espn_ufc.py` con `respx` (mock httpx):
  - [x] Listar eventos devuelve lista no vacía.
  - [x] Detalle evento devuelve los 14 combates con `matchNumber` ordenado y `cardSegment`.
  - [x] Parser de `status.type.state` distingue `pre`/`in`/`post`.
  - [x] Backoff retry en 429/5xx.
  - [x] Circuit breaker abre tras N fallos consecutivos.
- [x] Script runnable `scripts/probe_espn.py` (smoke manual: próximo evento + número de combates).
- [ ] Validación: alta del atleta para mostrar nombre en alerta. (pendiente — ver notas)

## Fase 1 — Scaffold ✅ (completada en Sesión 2)

- [x] `pyproject.toml` con todas las deps runtime + dev y rutas de paquete (`src/app`)
- [x] `docker-compose.yml` (postgres 16, redis 7, app)
- [x] `Dockerfile` (Python 3.12-slim)
- [x] `.env.example` con todas las vars
- [x] `src/app/main.py` mínimo (FastAPI + healthcheck `/health`)
- [x] `src/app/config.py` con pydantic-settings (carga de `.env`)
- [x] `src/app/db/session.py` con engine async SQLAlchemy
- [x] `alembic` inicializado (`alembic.ini` + `env.py` + primera migración vacía `0001`)
- [x] `AGENTS.md` con comandos frecuentes
- [x] `.gitignore` (python, .venv, .env, __pycache__, .pytest_cache, etc.)
- [ ] CI básico GitHub Actions (lint + tests) — opcional, para más adelante
- [x] **Verificación**: `pip install -e .[dev]` ✅ + `pytest` (2/2 pasan) ✅ + `ruff check src` ✅ + `uvicorn app.main:app` responde `/health` ✅. `docker compose up -d` pendiente (requiere reiniciar Windows para activar Docker Desktop).
- [ ] `alembic upgrade head` pendiente (requiere Postgres levantado).

## Fase 2a — EstimatorEngine puro ✅ (completada en Sesión 4)

- [x] `domain/entities.py` (Bout, Card, EstimatedStart, Subscription)
- [x] `engine/estimator.py` con lógica pura de recálculo:
  - [x] transición `pre → in` del combate previo → estimación por duración media.
  - [x] transición `in → post` del combate previo → `start = now + buffer_intercombate` (D18).
  - [x] regla "X minutos antes" configurable por suscripción.
- [x] **Tests aislados** con reloj fake (`freezegun`) y provider fake; sin Redis, sin BD.

## Fase 2b — Poller + idempotencia ✅ (completada en Sesión 4)

- [x] `engine/state.py` con Redis (registro de alerta ya disparadas): `SET alert:{sid}:{bid}:{status} 1 EX {ttl}` (D16).
- [x] `engine/poller.py` orquesta provider → estimador → idempotencia → notifier → BD.
- [x] `notifiers/dummy.py` (log-only) para validar sin llamadas reales.
- [x] `notifiers/base.py` con interfaz `VoiceNotifier` + `AlertPayload`/`CallResult`.
- [x] Modelos BD: `users`, `sport_subscriptions`, `event_subscriptions`, `bout_subscriptions`, `alert_log` con UNIQUE constraint `(subscription_id, bout_id, fired_at_hour)` (D16).
- [x] Reintentos 1 s/5 s/30 s con backoff (D17) en el Poller (delays inyectables para tests).
- [x] **Tests end-to-end** simulando transiciones de estado del combate previo.
- [x] Migración Alembic `a3657c6166f0` aplicada (SQLite dev).

## Fase 3 — Multiusuario + admin web ✅ (completada en Sesión 4)

- [x] Esquema BD completo + migraciones Alembic (extiende lo de Fase 2b).
- [x] Auth JWT (registro / login) con passlib[bcrypt] + PyJWT.
- [x] API REST: auth (register/login), users (admin), subscriptions (CRUD), alerts (list).
- [x] Panel admin Jinja2 + HTMX (D21): login, dashboard, usuarios, alertas.
- [x] **Web de usuario funcional** (`/app/*`): registro, login, dashboard, browsing
      de eventos ESPN, tarjeta de combates con botón "Crear alerta" (autodetección
      del combate previo), mis suscripciones, historial de alertas.
- [x] Tests de integración API + BD test (SQLite en memoria + TestClient).

## Fase MVP-launch — Lanzamiento (Sesión 5) ✅ (código listo; deploy pendiente de ejecutar)

Objetivos del owner: (1) ver próximas peleas con cara y nombre de cada peleador,
(2) login/logout de usuario + acceso a sus datos desde admin, (3) Twilio y
llamadas en el momento adecuado.

- [x] `get_athlete()` en `Provider`/`EspnUfcProvider` + `AthleteRef.athlete_id` + DTO `AthleteDetail` (nombre + headshot con fallback CDN).
- [x] `AthleteResolver` con caché Redis (TTL 7 días) + memoria compartida + lote limitado a 4 concurrentes (D32). Degrada a "TBD" sin cachear fallos.
- [x] `event_detail.html` rediseñada: foto de cara + nombre por esquina (rojo/azul) con placeholder SVG si falta imagen. Verificado en vivo: 28 headshots + nombres reales.
- [x] `TwilioNotifier` con TwiML inline `<Say es-ES>` ×2 + `asyncio.to_thread` (D30).
- [x] Factory `build_notifier()` gated por env-vars Twilio → Dummy si faltan (D30).
- [x] Poller cableado con datos reales: carga `User` (teléfono E.164), nombres de peleadores y nombre del evento en el payload. Salta usuarios sin teléfono/inactivos. Bugfix: usaba el id del competitor en vez del id del atleta.
- [x] Scheduler APScheduler in-process en `lifespan` (D31), `SCHEDULER_ENABLED` para desactivar.
- [x] Teléfono obligatorio + validación E.164 en registro web y API (D34).
- [x] Admin: `/admin/users/{id}` (detalle con teléfono, suscripciones, alertas) + activar/desactivar usuario.
- [x] Config producción: normalización `DATABASE_URL` de PaaS a asyncpg, guard de `JWT_SECRET` en producción.
- [x] `railway.json` + Dockerfile producción (migraciones + uvicorn `--workers 1`).
- [x] Tests: 72/72 (22 nuevos) · ruff · black · mypy ✅. Smoke E2E en vivo verificado.
- [ ] **Deploy real en Railway** (crear proyecto, add-ons PG+Redis, env-vars) — requiere cuenta del owner.
- [ ] Credenciales Twilio (cuando el owner tenga cuenta) → set env-vars y listo.

## Fase 4 — Boxeo/Tenis reales (fuera del MVP)

- [ ] Implementar `scrap_tennis.py` (flashscore/tennistemple) si ampliamos a tenis.
- [ ] Boxeo: integrar si TheSportsDB o ESPN cubren la card ordenada.
- [ ] Bellator/PFL: usar TheSportsDB (D12).
- [ ] Tests con HTML fixtures grabados.

## Fase 5 — VoiceNotifier real ✅ (adelantada en Sesión 5, D30)

- [x] Implementar `TwilioNotifier` (D23) con `twilio` SDK — gated por config (D30).
- [x] Plantilla TTS del mensaje: "El combate X contra Y de UFC XXX empieza en unos N minutos".
- [x] Tests con mocks de la API de Twilio.
- [ ] Verificación con llamada real (pendiente de cuenta Twilio del owner).

## Fase 6 — Rediseño visual + landing dinámica (Sesión 6, D35) 🔶 en curso

Objetivo del owner: dar un lavado de cara vistoso/llamativo a la web y añadir
una landing pública dinámica en `/`. Construido **sobre Jinja2** (sin migrar a
SPA — ver D35), sin build step.

- [x] Skills de agente: subset frontend de `addyosmani/agent-skills` instalado
      en `.opencode/skills/` (`frontend-ui-engineering`, `performance-optimization`,
      `code-review-and-quality` + `references/accessibility-checklist.md`).
- [x] `StaticFiles` montado en `/static` (`main.py`); antes no existía carpeta `static/`.
- [x] Tipografía **Inter Variable** auto-hospedada en `static/fonts/inter-var-latin.woff2`
      (~48KB, vía `@font-face` con eje de peso, `font-display: swap`).
- [x] CSS extraído de `base.html` a `static/css/app.css`: design tokens (color,
      spacing, radios, tipografía, motion, sombras) + refresco de todos los
      componentes existentes (nav, card, table responsive con `.table-wrap`,
      badge, fight/fighter, form/input/button) + utilidades para eliminar el
      CSS inline repetido (`.nav-user`, `.inline-form`, `.btn-sm`, `.event-row`,
      `.card-error`, `.empty-state`...).
- [x] Accesibilidad: skip-link, foco visible, `prefers-reduced-motion`, labels
      visibles en los 3 formularios de auth (antes solo placeholder).
- [x] `landing.html` **rediseñada a pantalla única (D36, reemplaza el diseño
      multi-sección inicial)**: `.hero-screen` a `100svh` sin scroll, póster
      oficial del evento (`static/img/hero.webp`/`hero.jpg`, generados con
      `ffmpeg` desde `imagen landing.jpeg`, ~160-200KB) como fondo full-bleed +
      overlay degradado + capa de partículas dinámicas (**tsparticles 2.12.0
      vía CDN**, guardado tras `prefers-reduced-motion`). Único CTA
      "Avísame" → `/app/register` con glow animado; enlace "Entrar" discreto
      arriba para usuarios existentes. `imagen landing.jpeg` suelta de la
      raíz eliminada (ya incorporada como `static/img/hero.*`).
- [x] `main.py`: `GET /` sirve la landing siempre (antes: 302 a `/app`, incluso
      con sesión activa se sigue mostrando la landing — decisión explícita).
- [x] Partial `templates/partials/_alert_cell.html` extraído de `event_detail.html`
      con atributos `hx-post`/`hx-target` ya preparados para HTMX.
- [ ] **Backend HTMX pendiente**: los endpoints `create_alert`/`delete_alert` en
      `src/app/web/user.py` aún no detectan la cabecera `HX-Request` para
      devolver el partial en vez del `RedirectResponse` 303 clásico — el HTML
      del partial ya tiene los atributos `hx-*` pero el submit todavía cae al
      fallback de recarga completa (funciona, pero sin el "sin recargar" real).
- [x] **Tests actualizados**: `test_root_redirects_to_app` (esperaba 302) en
      `tests/test_health.py` y `tests/test_api.py` reescritos como
      `test_root_serves_landing` (200 + contiene "Avísame"). **72/72 tests
      verdes**, `ruff`/`black`/`mypy` limpios.
- [ ] Smoke visual manual completo (landing de pantalla única + auth +
      dashboard + event_detail con fotos, responsive 320/768/1024/1440,
      contraste de texto sobre imagen, foco de teclado, comportamiento de
      partículas en pantallas pequeñas) — solo verificado parcialmente vía
      `curl`/`Invoke-WebRequest` (200 OK en `/`, contiene "Avísame" y script
      de tsparticles, imágenes hero sirven con el tamaño esperado).
- [x] `reveal.js` y `data-reveal`/`reveal-init` (de la landing multi-sección
       original) eliminados por dead code — ya no queda ninguna plantilla que
       los use.

**↵ Pivot a app (Sesión 7, D37): Fase 6 congelada.** Web de usuario y landing quedan como están (funcionales, sin nuevas features). Se abandona el HTMX pendiente y el smoke visual. El foco se traslada a Fase 7 (app móvil).

---

## Fase 7 — App móvil Android (React Native + Expo) 🔶 plan detallado (17 decisiones vía grilling, D37)

### Fase 7-Spike — Validación bypass-silent (solo sonido) ✅ COMPLETADA (Sesión 11)

**Alcance reducido (D39, revisado Sesión 8):** validar que `TYPE_ALARM` suena con el móvil en DnD. Sin FCM, sin full-screen, sin carátula.

**Historial hecho (Sesión 8):**
- [x] `mobile/` con `npx create-expo-app --template blank-typescript`.
- [x] `App.tsx`: 1 pantalla negra, 2 botones (Probar/Parar) + estado del servicio.
- [x] `npx expo prebuild --platform android` → `mobile/android/`.
- [x] Native module Kotlin en `alarm/`: `AlarmModule.kt` (canal `IMPORTANCE_HIGH` + `setBypassDnd`, expone `startAlarm`/`stopAlarm`), `AlarmService.kt` (foreground `mediaPlayback`, `RingtoneManager.TYPE_ALARM` loop, `USAGE_ALARM`, `PARTIAL_WAKE_LOCK` 10 min, notification `CATEGORY_ALARM` + `setSilent(true)`), `AlarmPackage.kt` + registro en `MainApplication.kt`.
- [x] `AndroidManifest.xml`: `FOREGROUND_SERVICE_MEDIA_PLAYBACK`, `POST_NOTIFICATIONS`, `WAKE_LOCK`, `VIBRATE`, `ACCESS_NOTIFICATION_POLICY` + `<service foregroundServiceType="mediaPlayback"/>`.
- [x] `eas.json` perfil `development` (APK `assembleRelease`), `mobile/README.md` troubleshooting.
- [x] EAS login (`theni55`), `eas init` → `@theni55/despertarme-spike` linkeado.
- [x] Build EAS #2 `FINISHED` ✅ (commit `81ca690`, cola ~6382 s free tier, Kotlin compiló limpio).
- [x] APK instalada en Android 14 físico, permiso notificaciones concedido.
- [x] **Prueba en móvil → CRASH ❌**: al tocar "Probar alarma" la app se cierra de golpe (crash de proceso nativo, no capturado por JS).

**Diagnóstico de la Sesión 9 (revisión de codebase):**

Causa casi segura del crash: **falta `android.permission.FOREGROUND_SERVICE`** en `AndroidManifest.xml:2` y `app.json:21-27`. Desde API 28, `startForeground()` sin el permiso genérico lanza `SecurityException` que **mata el proceso entero**, fuera del try/catch del bridge JS-Native. La excepción salta en `AlarmService.kt:32` (`startForeground`). Encaja 100% con los síntomas: no hay mensaje de error capturado, la UI alcanza a mostrar "stopped" antes de morir.

**Defensivos adicionales (misma build):**
1. `AlarmService.kt:45`: `RingtoneManager.getRingtone()` puede devolver null → NPE. Null-check con error legible vía callback al JS.
2. `AlarmModule.kt:46-48`: `promptPolicyAccess()` lanza Settings de DnD justo antes de `startForegroundService` → manda la app a background + innecesario (el bypass DnD funciona con el canal solo, bitacora:410). Mover a botón aparte o eliminar del flujo.
3. `AlarmService.kt:50`: `isLooping` requiere API 28+. Guard con `Build.VERSION.SDK_INT`.

**Nuevo flujo de validación (D41 — emulador-primero):**

Sin Android Studio aún → el continuador instala Android Studio + emulador API 34 (Google APIs):

- [x] Instalar Android Studio + SDK + emulador API 34 Google APIs (~5-8 GB) + verificar virtualización activada (Windows: Hyper-V/HAXM). Requisito previo: JDK 17. *(Sesión 10: SDK portable sin admin. Sesión 11: VT-x BIOS activado por owner → WHPX operativo.)*
- [x] `npx expo run:android` — compila en local (~2-5 min, vs ~2 h EAS) e instala en emulador. *(Sesión 11: `gradlew assembleDebug` 2m29s + Metro + `adb reverse` — `gradlew` directo no empaqueta JS bundle, ver handoff Sesión 11 hallazgo 1.)*
- [x] **Reproducir el crash** en emulador + `logcat` para confirmar (o refutar) la hipótesis `SecurityException` por `FOREGROUND_SERVICE`. *(Sesión 11: hipótesis confirmada — sin `FOREGROUND_SERVICE`, `startForeground` lanza SecurityException. Tras fix, no crash.)*
- [x] **Fix**: añadir `<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>` en `AndroidManifest.xml` + `app.json` permissions. *(Sesión 10: commit `e896b88`.)*
- [x] **Defensivos**: null-check `getRingtone`, quitar prompt Settings de `startAlarm`, guard API 28 en `isLooping`. *(Sesión 10: mismo commit.)*
- [x] **Validar en emulador con DnD/silencio**:
  - Activar DnD en Settings del emulador. *(Sesión 11: `adb shell cmd notification set_dnd priority` = "Alarms only" / `zen_mode=1`.)*
  - Tocar "Probar alarma" → suena `TYPE_ALARM` con `USAGE_ALARM`. *(Sesión 11: ✅ MediaPlayer `state:started`, AudioTrack frames delivered, logcat limpio.)*
  - "Parar" → silencio + foreground service termina limpio + notificación desaparece. *(Sesión 11: ✅ service destruido, player released, notificación retirada.)*
- [ ] **Validar Doze** (para D40): `adb shell dumpsys deviceidle force-idle` + verificar que `setAlarmClock` (cuando se implemente en 7b) despierta puntualmente. *(Pendiente — entra en Fase 7b con `AlarmScheduler`.)*
- [x] Build EAS → descargar APK → instalar en el **móvil Android 14 físico del owner**. *(Sesión 11: build EAS `fa4366ee` finalizada e instalada en hardware. Confirmado fix E1 sin crash + bypass DnD funcionando — mismo comportamiento que el emulador AOSP.)*
- [x] **Smoke OEM** en el dispositivo real: DnD, silencio total, sonido, parar. *(Sesión 11/16: ✅ confirmado en Android 14 físico del owner — sin quirks OEM observados. Spike 100% cerrado: emulador ✅ + físico ✅.)*

### Fase 7a — Backend: device model + JSON endpoints + FCM notifier (D40 ampliado) ✅ COMPLETADA (Sesión 12)

**Resumen ejecutivo (Sesión 12, 2026-07-16):** pivot User/Twilio → Device/FCM ejecutado end-to-end. 78 tests verdes (10 intactos de ESPN + 15 estimator + 7 athletes + 15 poller reescritos + 8 notifiers FCM + 15 API reescritos + 3 events route + 1 health + 4 ESPN extras), `ruff` / `black` / `mypy` limpios, migración Alembic `f7a0001_devices` aplicada en SQLite dev. Smoke HTTP: server levanta con los 9 endpoints (`/api/devices`, `/api/devices/me`, `/api/devices/me/test-alarm`, `/api/events`, `/api/events/{id}`, `/api/subscriptions`, `/api/alerts`, `/health`).

**Borrados (era User/Twilio/web):** `src/app/auth/` (3 ficheros), `notifiers/twilio.py`, `api/routes/auth.py` + `users.py`, `db/models/users.py`, `scripts/seed_admin.py`, `src/app/web/__pycache__/` (3 .pyc huérfanos), `db/models/subscriptions.py::SportSubscription` + `EventSubscription` (tablas muertas). Deps quitadas: `passlib[bcrypt]`, `bcrypt<5.0`, `pyjwt`, `twilio`, `pydantic[email]` (baja a `pydantic`). Añadida: `firebase-admin>=6.5`.

**Migrados/creados:** `db/models/devices.py` (Device nuevo), `db/models/subscriptions.py`/`alert_log.py` mutados (device_id, fired_at_epoch_hour, UNIQUE `(device_id, bout_id)`, sin previous_bout_id), `api/schemas.py` reescrito (DeviceCreate/Out, EventSummaryOut con image_url:None D42, EventCardOut), `app/security/device.py` (`get_current_device` vía X-Device-Id — estricto, no autocreate), `app/common/ids.py` (`new_uuid` mudado de auth/), `api/routes/devices.py` (POST register/upsert, DELETE me, POST test-alarm), `api/routes/events.py` (GET lista con caché Redis 5 min, GET detalle con `previous_bout_id` server-side E4), `notifiers/base.py` (PushNotifier/PushResult/AlertPayload data-only), `notifiers/dummy.py` (sin phone), `notifiers/fcm.py` (firebase-admin data-only high-priority), `notifiers/__init__.py` (build_notifier gating FCM + get_notifier singleton).

**Bugfixes E2–E8 aplicados en poller/estimator/state/provider:**
- E2 — `estimator.estimate` ahora acepta `observed_at`; `AlertState.remember_transition/get_transition` persisten el anclaje in→post en Redis (TTL 24 h). El poller pasa `observed_at` al estimador. Test `test_poller_e2_estimation_anchored_to_first_observation` valida que la estimación no se desliza.
- E3 — `_process_subscription` comprueba el estado del target: si `in` → push `started` (idempotente); si `post` → push `cancelled` + marca sub como `fired`. Tests `test_poller_e3_pushes_started_when_target_in` + `test_poller_e3_pushes_cancelled_when_target_post_and_marks_fired`.
- E4 — `BoutSubscription` ya no persiste `previous_bout_id`; el poller deriva `prev = card.previous_bout(target)` en cada poll. `api/routes/events.py` calcula `previous_bout_id` server-side (matchNumber+1) y lo devuelve al cliente.
- E5 — `EspnUfcProvider._request` solo llama `_on_failure()` si `_is_retryable(exc)`: 404 y 4xx (no 429) NO abren el circuit breaker. Test `test_e5_circuit_breaker_does_not_open_on_4xx` confirma con 5 peticiones inválidas.
- E6 — `AlertLog.fired_at_hour` → `fired_at_epoch_hour` (`int(now.timestamp())//3600`), UNIQUE `(subscription_id, bout_id, fired_at_epoch_hour)` preservada, UNIQUE `(device_id, bout_id)` añadida en `bout_subscriptions`. Idempotencia marcada **tras** éxito (no antes).
- E7 — `RETRY_DELAYS = (2.0,)` (1 retry corto, antes 1/5/30 s = 36 s). Scheduler `misfire_grace_time=120` para no descartar ticks. Test `test_poller_e7_retries_cut_short_on_failure` valida 2 intentos máx.
- E8 — `poll_once` agrupa subs por `event_id` y cachea la Card por ciclo: 1 fetch ESPN/evento/ciclo en vez de N. Tests validan múltiples subs del mismo evento con un solo card load.
- D40 push on-change — el poller solo empuja `update` si la estimación se movió >`MIN_DELTA_SECONDS=60` desde el último push (`AlertState.get_last_estimate/set_last_estimate`). `started`/`cancelled` son idempotentes (una vez por sub+bout).

**Pendiente externo (no bloquea Fase 7b):** Firebase project + service account JSON + `google-services.json` para la app (manual del owner).

**Verificación final:** `ruff check src tests` ✅ · `black --check src tests` ✅ · `mypy src/app` ✅ · `pytest` **78/78 verdes** · `alembic upgrade head` en SQLite dev ✅ · smoke TestClient `/health` + `/openapi.json` 9 paths ✅.

**Code review post-merge (Sesión 13, 2026-07-16) — 4 fixes aplicados:** review multi-eje del commit `6470b24` con veredicto request-changes. Arreglados con test de regresión: (1) **Critical** — `FcmNotifier` inicializaba app Firebase *nombrada* pero `messaging.send` sin `app=` resolvía contra la default inexistente → 100% de envíos reales fallarían (`send(message, False, self._app)`); (2) caché de `GET /api/events` con clave única servía resultados de una query a otra con distinto `include_past_hours` (ahora solo cachea la default); (3) auth de `X-Device-Id` no normalizaba a lowercase como el registro → 401 con UUIDs en mayúsculas; (4) `inst_user_settings.tmp` (temporal de Android Studio) fuera del repo + `*.tmp` en `.gitignore`. **80 tests verdes** tras los fixes. Deuda registrada en handoff Paso 3: `message_type` en UNIQUE de alert_log (los `update` D40 del mismo sub/hora chocan y se pierden filas de auditoría), UUID v4 estricto en `DeviceCreate`, nits menores.

**Eliminar era User/Twilio:**

- [ ] **Preparación previa (antes de borrar `auth/`)**: mover `new_uuid()` de `auth/dependencies.py:57` a un util neutro (lo importa `subscriptions.py:13` y `auth.py:11` — si se borra `auth/` en bloque, `subscriptions.py` deja de importar).
- [ ] Limpiar `config.py:71-79`: el `model_validator` de producción referencia `jwt_secret` — quitar el campo Y el validator juntos para que la app arranque. Añadir settings FCM (`FCM_CREDENTIALS_PATH` o `FCM_CREDENTIALS_JSON`).
- [ ] Eliminar `User` model, `auth/` completo (security, validators, dependencies), routers `/api/auth/*` y `/api/users/*`, `notifiers/twilio.py`.
- [ ] Quitar deps de `pyproject.toml`: `passlib[bcrypt]`, `bcrypt<5.0`, `pyjwt`, `twilio`, `pydantic[email]` (solo lo usaba `UserCreate`). Añadir `firebase-admin`.
- [ ] Eliminar `scripts/seed_admin.py` (password hardcodeada + apunta a rutas web que ya no existen).
- [ ] Limpiar `src/app/web/__pycache__/` (`.pyc` huérfanos de la era web).

**Migración Alembic — escribir a mano contra Postgres:**

⚠️ La migración base `a3657c6166f0` se autogeneró contra SQLite. Las FKs no tienen naming convention (`Base` no define `metadata.naming_convention`). Hacer a mano:

- [ ] **Crear tabla `devices`**: `id` (UUID PK), `fcm_token`, `platform`, `timezone`, `locale`, `is_active`, `created_at`, `last_seen_at`.
- [ ] **Renombrar FKs en `bout_subscriptions` y `alert_log`**: `user_id` → `device_id` + FK a `devices`. ⚠️ Hay 5 FKs con `ondelete='CASCADE'` → si se dropea `users` antes de migrar datos, se borran suscripciones y alert_log en cascada. Orden correcto: crear `devices` → migrar datos → dropear FK vieja → renombrar columna → crear FK nueva → dropear `users`.
- [ ] **Tablas `sport_subscriptions` y `event_subscriptions`**: también tienen FK a `users` (`subscriptions.py:21-39`). El plan no las menciona pero existen. Decidir: eliminar tablas enteras (ningún router las usa — parecen muertas) o renombrar FK también.
- [ ] **Eliminar `users`**: antes, `sa.Enum(name='user_role').drop(op.get_bind())` explícito (Alembic no lo detecta en autogenerate y el ENUM queda huérfano en PG).
- [ ] **Índices**: renombrar `ix_bout_subscriptions_user_id` → `ix_bout_subscriptions_device_id`, ídem `alert_log`.
- [ ] Añadir **UNIQUE `(device_id, bout_id)`** en `bout_subscriptions` — sin esto, un tap de re-suscribirse en la app genera push duplicados.
- [ ] **`fired_at_hour` → `fired_at_epoch_hour`** (`epoch//3600`) en `alert_log`: `now.hour` colisiona entre días distintos a la misma hora (IntegrityError espurio) y permite duplicado si un retry cruza el cambio de hora.

**Device auth y endpoints:**

- [ ] `get_current_device` (header `X-Device-Id`) reemplaza a `get_current_user` en `subscriptions.py` y `alert_log.py`.
- [ ] `POST /api/devices` (registro), `DELETE /api/devices/me`, `POST /api/devices/me/test-alarm`.
- [ ] `GET /api/events` (lista con caché Redis + filtro por fecha — `list_upcoming_events` actual no filtra pasados y es N+1 secuencial, `espn_ufc.py:175-196`).
- [ ] `GET /api/events/{id}` (tarjeta con bouts, fotos/nombres vía `AthleteResolver`, y **`previous_bout_id` calculado server-side** — el cliente no debe mandarlo, `schemas.py:46-52` hoy lo exige).

**Contrato FCM (D40):**

- [ ] `notifiers/fcm.py` con `firebase-admin`. Payload data-only con `type` (`update`/`started`/`cancelled`) + `estimated_start_at` + `bout_id` + `event_id` + `fighters` + `event_name`. `build_notifier()` gated por `FCM_CREDENTIALS` → `DummyNotifier` (mismo patrón D30 que Twilio).
- [ ] **Configurar proyecto Firebase** (consola, service account key Python, `FCM_CREDENTIALS` env-var, `google-services.json` para la app).

**Refactor Poller (fixes de bugs encontrados en Sesión 9):**

- [ ] **E2 — Anclar estimación `post` a primera observación** (`estimator.py:111-118`): hoy `start_at = now + buffer` se recalcula en cada poll → `delta` constante = 300 s → `should_fire` nunca se cumple con `lead < 5 min`. Con D40 esto muta: el backend ya no dispara "ring now" sino que pushea `estimated_start_at`, pero si la estimación se desliza hacia delante cada poll, la alarma local se reprograma al infinito. **Fix**: persistir `observed_at` (timestamp de la transición `in→post`) en Redis y calcular `start_at = observed_at + buffer`, relativo a un momento fijo.
- [ ] **E3 — Guard del estado del combate objetivo** (`poller.py:104-122`): hoy solo mira el previo. Si el target ya está `in`/`post` (servidor arrancó tarde, Redis se vació, sub creada a mitad de evento), el poller debe pushear `started`/`cancelled`, no una estimación fantasma.
- [ ] **E4 — Derivar `previous_bout_id` server-side** desde la card fresca en cada poll (el `subscriptions.py:43` congela lo que mandó el cliente; las reordenaciones día-de-evento de UFC producen estimaciones incoherentes silenciosas). Aprovechar para quitarlo del contrato del cliente → simplifica la API móvil.
- [ ] **E6 — Idempotencia reforzada**: `fired_at_hour` → `epoch//3600` (ver migración arriba) + UNIQUE `(device_id, bout_id)`. Reconsiderar si marcar idempotencia antes o después de notificar: para FCM (más barato que voz), marcar tras éxito y confiar en UNIQUE de BD puede ser mejor estrategia.
- [ ] **E7 — Retries D17 recortados para FCM**: los 3 intentos con sleep acumulado de 36 s (`poller.py:216-218`, bloquean el ciclo entero del poll) no tienen sentido para push (idempotente, barato, sin estado de sesión). Reducir a 1 retry corto o eliminar. Ajustar `misfire_grace_time` del scheduler para no descartar ticks.
- [ ] **E5 — Circuit breaker solo con fallos retryables** (`espn_ufc.py:150-156`): hoy cuenta 404s y cualquier excepción → 5 requests a un `event_id` inválido desde el endpoint público `GET /api/events/{id}` tumban poller + API 60 s (DoS trivial). Contar solo 429/5xx/transporte.
- [ ] **E8 — Caché de card por ciclo en `poll_once`**: agrupar subs por `event_id` → 1 fetch ESPN/min en vez de N.
- [ ] **Validación server-side de `lead_minutes`**: con valor mínimo sensato (≥1, o ≥5 si no se arregla E2).

**Poller con Device:**

- [ ] Carga `Device` (fcm_token, timezone, locale) en vez de `User`, skip `is_active==False` o `fcm_token is None`.
- [ ] **Push on-change (D40)**: el poller pushea FCM cuando la estimación se mueve >~1 min (± lead conservador), no solo en el umbral del lead. Esto relaja la criticidad de la latencia del poller.
- [ ] `_call_with_retries` adaptado a FCM (payload sin `phone`/`user_id`; token + data dict).

**Tests:**

- [ ] Reescribir `test_poller` (device en vez de User, payload cambiado) + `test_api` (nuevos endpoints, X-Device-Id) + `test_notifiers` (FCM mockeado, mismo patrón que Twilio). `test_estimator`, `test_espn_ufc`, `test_athletes` sobreviven intactos (~31 tests).
- [ ] **Añadir tests para los bugs E2/E3/E4** (lead < 5 en post, target ya empezado, previo incoherente) — hoy sin cobertura.
- [ ] Verificación completa: `ruff`/`black`/`mypy`/`pytest`.

### Fase 7b — App Android v1 Kotlin nativo + Jetpack Compose (D40/D41/D43) 🔶 en curso

**Stack definitivo (D43, pivot desde Expo/RN de D37):** Compose BOM 2024.12 + Kotlin 2.0.21 + AGP 8.7.3 + Gradle 8.11.1 (compila con `gradlew assembleDebug` desde CLI, sin IDE — D44), Retrofit 2.11 + `converter-kotlinx-serialization` oficial, Coil 2.7, DataStore Preferences 1.1, Navigation Compose 2.8, Material3, `firebase-messaging` en el tramo FCM. `mobile/` spike Expo renombrado a `mobile-expo/` (preservado en git, no se toca); nuevo scaffold en `mobile-kotlin/` paquete `com.despertarme.app`.

**Paso 1 — Scaffold + Home/EventDetail navegables (Sesión 15) ✅**

- [x] `git mv mobile mobile-expo` (preserva spike Expo en WD, refs en historial).
- [x] Scaffold `mobile-kotlin/` a mano (sin wizard IDE): `settings.gradle.kts`, `build.gradle.kts`, `gradle/libs.versions.toml`, wrapper Gradle 8.11.1 (jar+scripts copiados del spike), `debug.keystore` generado con `keytool`.
- [x] `DespertarMeApp.kt` (Application: canal `IMPORTANCE_HIGH` + `setBypassDnd` al crear).
- [x] `MainActivity.kt` (single-activity Compose + `enableEdgeToEdge`).
- [x] `ui/theme/`: tokens color (`#E50914`, `#0A0A0A`) + Typography sans-serif (Inter sin embeber todavía) + `DespertarTheme` dark-first.
- [x] `AlarmService.kt` portado del spike a paquete `com.despertarme.app.alarm` (mismo `TYPE_ALARM` + `USAGE_ALARM` + `setBypassDnd` validado en Sesión 11).
- [x] `AndroidManifest.xml` con `usesCleartextTraffic=true` (necesario para `http://10.0.2.2:8000/` en API 28+), permisos `FOREGROUND_SERVICE_MEDIA_PLAYBACK` + `USE_EXACT_ALARM` + `USE_FULL_SCREEN_INTENT` + `RECEIVE_BOOT_COMPLETED` + los del spike.
- [x] `data/remote/`: interfaces Retrofit `DespertarApi` (9 endpoints) + DTOs `@Serializable` (`EventCardOut`, `BoutOut`, `BoutAthleteOut`, `DeviceCreate`, `BoutSubscriptionCreate`) + `DeviceIdInterceptor` (header `X-Device-Id`).
- [x] `data/DeviceStorage.kt`: DataStore Preferences con UUID v4 persistente (`ensureDeviceId()` + `getDeviceId()` + `fcmToken()`).
- [x] `data/AppContainer.kt`: single OkHttpClient con baseUrl `http://10.0.2.2:8000/`, Json con `ignoreUnknownKeys`, registro best-effort en `ensureRegistered()` (placeholder token `no-fcm-yet-{uuid}` hasta tramo FCM).
- [x] `ui/viewmodel/EventDetailViewModel.kt` + `EventDetailViewModelFactory` (inyección manual de `AppContainer`).
- [x] `ui/screens/HomeScreen.kt`: hero `drawable-nodpi/hero.webp` (extraído de la rama `web`, D36/D42) + `Modifier.background` veil degradado + botón "Avísame" (navega a EventDetail del próximo evento) + botón secundario "Probar sonido" (arranca `AlarmService`).
- [x] `ui/screens/EventDetailScreen.kt`: `LazyColumn` de combates, cada `BoutCard` con `matchNumber` + `cardSegment` chip + `weightClass` + `periods`; columnas rojo/azul con `AsyncImage` (Coil) para `headshot_url` + `name`; `FlowRow` de `FilterChip` para selector 5/10/15/30/60; botón "Avisarme" → `POST /api/subscriptions`; estado "Avisando ✓" tras suscripción; Snackbar "Alerta creada: X vs Y — N min" vía `SnackbarHostState` + `LaunchedEffect`.
- [x] `MainActivity.kt` con `AppGraph` (NavHost home → event/{eventId}): resuelve próximo evento concurrente en `LaunchedEffect`, pasa `container` y `vm` por factory.

**Build verification (Sesión 15):**
- [x] 3 iteraciones de `./gradlew assembleDebug` en local — BUILD SUCCESSFUL (1:43 primera con descarga Gradle 8.11.1 + deps, 22-46s posteriores incremental). Tres fixes aplicados: `getByName("debug")` en lugar de `create` (AGP ya tiene default), converter oficial `com.squareup.retrofit2:converter-kotlinx-serialization` en lugar de Jake Wharton, import `FlowRow` desde `androidx.compose.foundation.layout` + `@OptIn(ExperimentalLayoutApi::class)`, y `Image(painterResource(...))` en HomeScreen en lugar de `AsyncImage(model: Painter?, ...)` (Coil no soporta Painter como model).
- [x] APK debug 21.9 MB en `app/build/outputs/apk/debug/app-debug.apk`.

**Smoke en emulador `pixel_6_api34` (Sesión 15):**
- [x] `adb install -r app-debug.apk` → Success.
- [x] `adb shell pm grant com.despertarme.app android.permission.POST_NOTIFICATIONS`.
- [x] `adb shell am start -n com.despertarme.app/.MainActivity` → activity visible (`topResumedActivity=com.despertarme.app/.MainActivity`), sin `FATAL` en logcat (tras fixes de `usesCleartextTraffic=true` + `Image` en lugar de `AsyncImage(Painter)`).
- [x] Backend SQLite levantado: `.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000` con cwd en raíz del repo (no `src/` — si no, pydantic-settings no encuentra `.env` y cae a defaults Postgres asyncpg rechazado). `alembic upgrade head` aplicado.
- [x] `adb reverse tcp:8000 tcp:8000` (puente emulador→host, además del `10.0.2.2` AOSP nativo).
- [x] Verificado en `uvicorn.out`: app realiza `POST /api/devices` (registro UUID) + `GET /api/events` (LaunchedEffect) desde puerto 55980, y tras `adb shell input tap 540 2150` → `GET /api/events/600059599` desde puerto 56063 (navegación Home→EventDetail exitosa, card con 12 combates reales UFC Fight Night Du Plessis vs Usman 2026-07-18).
- [x] Verificado en SQLite: device `e57d6077-7ef4-4e68-bb99-8d9d8a2ae174` registrado por la app (platform=android, locale=es-ES, fcm_token=`no-fcm-yet-...`).

**Paso 2 — AlarmScheduler + AlarmActivity + verify-then-ring (Sesión 18 ✅, modelo revisado D45)**

- [x] **`AlarmScheduler`** (nuevo, D40): `AlarmManager.setAlarmClock()` a `estimated_start_at − lead_minutes`. Requiere permiso `USE_EXACT_ALARM` (auto-concedido en Play por ser alarm app, ya en manifest). Persistencia de alarmas programadas en DataStore (para re-programar tras reboot).
- [x] **`AlarmReceiver`** (BroadcastReceiver): al disparar la alarma → arranca `AlarmService` + abre `AlarmActivity` (full-screen intent). Marca `fired=true` para ring-once D45. Sin verify-then-ring (ya no necesario: la alarma solo se programa con estimación real del backend, no con fecha oficial de ESPN).
- [x] **`AlarmActivity`** (full-screen): "X vs Y — UFC {event} empieza en ~N min" + botón "Descartar" (stop service). `setShowWhenLocked` + `setTurnScreenOn`. Compose.
- [x] **BootReceiver** (`RECEIVE_BOOT_COMPLETED`): re-programa alarmas tras reinicio del dispositivo.
- [ ] **Doze validation**: `adb shell dumpsys deviceidle force-idle` → verify `setAlarmClock` despierta puntualmente. (Pendiente — el smoke E2E con evento real del 18 jul validará este punto también).
- [x] **Cushion +1 min siempre** (D45): aplicado en `handleUpdate()` sobre `est-lead+60s` con floor `now+60s`. Verificado en smoke del 17/18 jul: push con `est=now+10min` + lead=5 → trigger=now+6min → alarma sonó a los 6:02 min exactos.
- [x] **Ring-once flag** (D45): `PendingAlarm.fired` marcado por `AlarmReceiver` al disparar; pushes `update` posteriores se ignoran. Verificado en smoke: logcat "Alarma disparada y fired=true marcado para bout=401889642".
- [x] **Smoke E2E en emulador** (17/18 jul 2026): endpoint debug temporal `POST /api/debug/simulate-transition` simuló transición ESPN con `estimated_start_in_minutes=10`. Pipeline completo verificado: backend → push `update` (epoch millis) → handleUpdate (cushion) → AlarmScheduler → setAlarmClock → 6 min tick → AlarmReceiver → AlarmService (sonido TYPE_ALARM) + AlarmActivity (full-screen sobre lockscreen). Tras el test, endpoint debug y su gate en `main.py` borrados. `pytest` 80/80 verdes tras borrado.

**Paso 3 — Pantallas restantes ✅ COMPLETADO (Sesión 17, 2026-07-17 — Fases B/C/D del plan `plan-mvp-android-fable5.md`)**

- [x] **Eventos** (`EventListScreen` + `EventListViewModel`): lista `GET /api/events`, tarjeta con franja degradada roja + nombre bold + fecha, tap → `event/{id}`.
- [x] **Mis Alertas** (`SubscriptionsScreen` + `SubscriptionsViewModel`): `GET /api/subscriptions` con nombres de peleadores resueltos vía fetch del evento + `DELETE /api/subscriptions/{id}` (verificado 204 + snackbar) + historial `GET /api/alerts`.
- [x] **Ajustes** (`SettingsScreen`): device_id + timezone + estado permisos (notificaciones, alarmas exactas) + toggle "Probar/Parar alarma" que arranca/para `AlarmService` local directamente (el `POST /api/devices/me/test-alarm` del backend requiere FCM — pendiente del tramo FCM).
- [x] **Bottom `NavigationBar`** Material3 con 4 destinos (Home/Eventos/Mis Alertas/Ajustes), acento `UfcRed`, integrada en `AppGraph` con `Scaffold`.
- [x] **Cliente API completado**: `@DELETE /api/subscriptions/{id}` + `@GET /api/alerts` + DTO `AlertLogOut`.
- [x] **Pulido visual Fase C**: badge `cardSegment` con color (main rojo / prelims azul), chip "PRÓXIMO" + borde rojo en el primer combate, `ArrowBack` AutoMirrored (fix deprecación).
- [x] **`AlarmService.ACTION_STOP`** añadido (gap descubierto en smoke: no había forma de silenciar el sonido de prueba desde la app). Botones de test ahora son toggle Probar/Parar en Home y Ajustes.
- [x] **AlarmScreen** (modal full-screen) — `AlarmActivity.kt` implementado en el Paso 2 (Sesión 18, modelo D45).
- [ ] Sonido custom embebido `res/raw/alarm.ogg` (~200-500KB) en lugar de `RingtoneManager.TYPE_ALARM` del spike.

**Smoke Sesión 17 (emulador `pixel_6_api34`, máquina `javier.romero`):** build verde sin warnings; 4 pestañas + detalle navegables sin FATAL; suscripción E2E desde la app (`POST /api/subscriptions` 201 → visible en Mis Alertas con "Anna Melisano vs Dione Barbosa" → `DELETE` 204 → empty state). Fix SSL corporativo del backend (truststore en venv, ver plan Fase B).

**Paso 4 — Tramo FCM (deps externas, D40)**

- [x] Firebase project (manual owner): service account JSON → `FCM_CREDENTIALS_JSON` backend + `google-services.json` en `mobile-kotlin/app/`. *(Sesión 18: Firebase project `despertarme-73d00` creado, credenciales colocadas.)*
- [x] Plugin `com.google.gms.google-services` + dep `com.google.firebase:firebase-messaging` (en `build.gradle.kts` y `libs.versions.toml`). *(Sesión 18: plugin + `firebase-messaging-ktx` 24.1.0 añadidos.)*
- [x] Cliente FCM: `FirebaseMessagingService` handler. Background: `update` → reprogramar `AlarmScheduler`; `started`/`cancelled` → notificación informativa. Foreground: `update` → actualizar UI. *(Sesión 18: `DespertarMeFirebaseService.kt` con `handleUpdate`/`handleStarted`/`handleCancelled`/`handleFire`.)*
- [x] Redis: `docker compose up -d` para desbloquear poller (idempotencia D16). *(Sesión 18: Docker Desktop + Redis corriendo, poller activo.)*

**Paso 5 — Validación final + deploy (Fase 7c)**

- [x] Backend en Railway (D33): `https://despertarme-production.up.railway.app`. `FCM_CREDENTIALS_JSON` + `APP_ENV=production` + PG + Redis add-ons configurados. *(Sesión 20: deploy operativo tras 3 fixes de migración + railway.json.)*
- [x] **Cambiar `baseUrl` en `AppContainer.kt`** de `http://10.0.2.2:8000/` a `https://despertarme-production.up.railway.app/`. *(Sesión 20: 1 línea cambiada, APK debug BUILD SUCCESSFUL 23.1 MB.)*
- [x] Móvil físico Android 14 (bypass DnD real + OEM quirks del owner). *(Sesión 21: test-alarm sonó en hardware físico. FCM entrega pushes reales al móvil — pipeline verificado end-to-end.)*
- [x] `./gradlew assembleDebug` recompilar APK tras el cambio de `baseUrl`. *(Hecho en Sesión 20. Release APK pospuesta al tramo Play Store.)*
- [ ] Smoke end-to-end: crear alerta → alarma local suena a la hora estimada en hardware físico con DnD/silencio. *(Sesión 21: test-alarm y push `update` del poller entregados al móvil. Falta validación con evento real → 25 julio 2026, UFC Fight Night Ankalaev vs Guskov.)*

### Fase 7c — Deploy + smoke real (Sesión 14 plan, reescrito con stack Kotlin; planificado Sesión 19 vía Opción C: Railway URL)

- [x] Backend en Railway (D33) con env-vars: `FCM_CREDENTIALS_JSON` + `APP_ENV=production`. PG + Redis add-ons operativos. *(Sesión 20: deploy exitoso en Railway. `JWT_SECRET` ya no aplica tras pivot Device sin auth JWT D37.)*
- [x] Cambiar `baseUrl` en `AppContainer.kt` de `http://10.0.2.2:8000/` a la URL pública de Railway. *(Sesión 20: 1 línea cambiada, APK debug compilada.)*
- [x] Firebase project + `google-services.json` en `mobile-kotlin/app/`. *(Hecho desde Sesión 18.)*
- [x] Smoke parcial: test-alarm verificado en hardware físico (Sesión 21: alarma sonó). Push `update` del poller entregado al móvil (Sesión 21: message_id real en alert_log). *(Falta smoke completo con evento real → 25 julio 2026.)*

### Fase 7d — iOS (post-MVP, D40 vía AlarmKit — rewrite SwiftUI, no reutiliza TS de D37)

- [ ] App iOS nativa SwiftUI (no Expo, D43 pivot descarta reutilizar pantallas TS). Build via Xcode (no EAS).
- [ ] **AlarmKit** (iOS 26+, WWDC25 sesión 230): `AlarmManager.schedule(id:configuration:)` con `Alarm.Schedule.fixed(date)`, título custom, sonido custom, botón secundario con App Intent para abrir la app. El sistema garantiza bypass de silencio y focus sin Critical Alert Entitlement — solo requiere `NSAlarmKitUsageDescription` en el plist y opt-in del usuario. Ciclo de vida completo: cancelar/reprogramar por id (mismo patrón que `setAlarmClock` en Android).
- [ ] Requisito mínimo iOS 26 (adopción mayoritaria esperada para cuando se ejecute esta fase). Sin fallback a Critical Alert — el entitlement es discrecional de Apple y lento.
- [ ] Mismo contrato API + Retrofit-equivalente en Swift (async/await + URLSession), mismo `device_id` UUID v4ersistente en Keychain.

---

## Fase 8 — Tenis (ATP/WTA) 🔶 en curso (Sesión 23, rama `feature/tenis`)

Plan detallado en `memoria/plan-tenis.md`. Decisiones D46-D49.

### Fase 8a — ESPN Tennis Provider

- [ ] `src/app/providers/espn_tennis.py`: `EspnTennisProvider(Provider)` — reutiliza circuit breaker + tenacity
- [ ] DTOs tenis en `providers/models.py`: `TennisCourt`, `TennisRound`, `Competitor.name`, `Bout.court`/`round`/`match_number` optional
- [ ] `providers/__init__.py`: exportar `EspnTennisProvider`
- [ ] `tests/test_espn_tennis.py` con respx + fixtures grabadas

### Fase 8b — Generalización del dominio (backward-compatible)

- [ ] `domain/entities.py`: `Bout.court`, `Bout.sport`, `Card.sport`, `Card.previous_bout()` por court+date
- [ ] `BoutStatus.sport`, `estimated_duration_seconds`/`elapsed_seconds` sport-aware

### Fase 8c — DB + API multi-sport

- [ ] `db/models/subscriptions.py`: columna `sport: str = "mma"`
- [ ] Migración Alembic autogenerada
- [ ] `config.py`: `espn_tennis_league`, `buffer_intermatch_tennis_seconds`
- [ ] `api/routes/events.py`: provider registry, `?sport=` query param (default "mma")
- [ ] `api/schemas.py`: `BoutOut` (court, sport, round_description), `BoutSubscriptionCreate`/`Out` (sport)
- [ ] `api/routes/subscriptions.py`: persistir `sport`

### Fase 8d — Poller + Scheduler multi-sport

- [ ] `engine/poller.py`: providers dict, agrupar por `(sport, event_id)`, mapeo sport-aware
- [ ] `scheduler.py`: construir dict de providers
- [ ] `main.py`: close de todos los providers

### Fase 8e — Tests + smoke

- [ ] Tests actualizados (test_poller, test_api, test_events_route) + `test_espn_tennis`
- [ ] `ruff` + `black` + `mypy` limpios
- [ ] `scripts/probe_tennis.py`

### Fase 8f — App Android

- [ ] `DespertarApi.kt`: `@Query("sport")` en listEvents/getEvent
- [ ] DTOs Kotlin: `BoutSubscriptionCreate.sport`, `BoutOut.court`/`roundDescription`
- [ ] Home: selector de deporte (tabs MMA / Tenis)
- [ ] EventDetail tenis: agrupado por court, badge round, nombres inline
- [ ] SubscriptionsScreen: badge de deporte
