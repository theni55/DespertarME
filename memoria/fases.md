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

### Fase 7-Spike — Validación bypass-silent (solo sonido) 🔶 en curso (Sesión 9)

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

- [ ] Instalar Android Studio + SDK + emulador API 34 Google APIs (~5-8 GB) + verificar virtualización activada (Windows: Hyper-V/HAXM). Requisito previo: JDK 17.
- [ ] `npx expo run:android` — compila en local (~2-5 min, vs ~2 h EAS) e instala en emulador.
- [ ] **Reproducir el crash** en emulador + `logcat` para confirmar (o refutar) la hipótesis `SecurityException` por `FOREGROUND_SERVICE`.
- [ ] **Fix**: añadir `<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>` en `AndroidManifest.xml` + `app.json` permissions.
- [ ] **Defensivos**: null-check `getRingtone`, quitar prompt Settings de `startAlarm`, guard API 28 en `isLooping`.
- [ ] **Validar en emulador con DnD/silencio**:
  - Activar DnD en Settings del emulador.
  - Tocar "Probar alarma" → suena `TYPE_ALARM` con `USAGE_ALARM`.
  - "Parar" → silencio + foreground service termina limpio + notificación desaparece.
- [ ] **Validar Doze** (para D40): `adb shell dumpsys deviceidle force-idle` + verificar que `setAlarmClock` (cuando se implemente en 7b) despierta puntualmente.
- [ ] Build EAS #3 → descargar APK → instalar en el **móvil Android 14 físico del owner**.
- [ ] **Smoke OEM** en el dispositivo real: DnD, silencio total, sonido, parar. Si falla en el dispositivo pero no en emulador → es un quirk del fabricante (Xiaomi/Samsung/etc.) y se aborda con los datos concretos de ese modelo.

### Fase 7a — Backend: device model + JSON endpoints + FCM notifier (D40 ampliado)

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

### Fase 7b — App Android v1 (Expo + Android Studio + emulador + dev build, D40/D41)

**Setup (Android Studio ya instalado — adelantado en D41):**

- [ ] Verificar que Android Studio + emulador API 34 funciona (ya debería estar desde el spike).
- [ ] `npx expo prebuild --platform android --clean` si se tocó `app.json` (bare workflow, ver `expo doctor` en handoff Sesión 8).

**Native module — alarma local + sonido:**

- [ ] **`AlarmScheduler`** (nuevo, D40): receiver `AlarmReceiver` + `AlarmManager.setAlarmClock()` que programa la alarma local a `estimated_start_at − lead_minutes`. Al disparar, verify-then-ring: fetch a `GET /api/events/{id}` → si el target sigue en `pre` y la estimación es < lead → arranca `AlarmService`; si ya empezó → notifica sin sonido; si se canceló/reprogramó → reprograma la alarma local. Permiso `USE_EXACT_ALARM` (auto-concedido en Play por ser alarm app, sin fricción de usuario).
- [ ] **Refactor del `AlarmService` del spike**: añadir sonido custom embebido (`res/raw/alarm.ogg`, ~200-500KB, en vez de `RingtoneManager.TYPE_ALARM` por defecto) + `AlarmActivity` (full-screen intent con `setShowWhenLocked`/`setTurnScreenOn` — ya no está en el spike, entra ahora con emulador para iterar).
- [ ] Permisos `AndroidManifest.xml`: se mantienen los del spike + añadir `USE_FULL_SCREEN_INTENT`, `USE_EXACT_ALARM`, `RECEIVE_BOOT_COMPLETED` (para re-programar alarmas tras reinicio). ⚠️ `FOREGROUND_SERVICE_DATA_SYNC` del plan original está **descartado** — tipo erróneo/restringido en Android 14+. Se usa `mediaPlayback` (ya probado en el spike) o `specialUse`.
- [ ] Cliente FCM: `@reactnative-firebase/messaging`. Handler background: recibir `update` → reprogramar `AlarmManager.setAlarmClock` (NO arrancar el service — la alarma local se encarga). Handler foreground: recibir `update` → actualizar UI; recibir `started`/`cancelled` → mostrar notificación informativa. `google-services.json` en `mobile/android/app/`.
- [ ] `expo-secure-store` para `device_id` (UUID v4 generado en 1ª launch).

**Pantallas (Expo Router Tabs: Home / Eventos / Mis Alertas / Ajustes):**
- [ ] **Home**: póster del próximo evento (hero full-bleed) + botón primario **"Avísame"** (→ EventDetail destacado) + botón secundario **"Eventos"** (→ lista).
- [ ] **Eventos**: lista de próximos UFC (card con imagen, fecha, nombre) desde `GET /api/events`.
- [ ] **EventDetail**: tarjeta de combates (foto+nombre, borde rojo/azul por esquina, matchNumber, segmento, peso), selector fijo de minutos (5/10/15/30/60). ⚠️ El backend debe validar `lead >= 5` si no se arregló E2 en Fase 7a. Botón "Avisarme" → `POST /api/subscriptions` (sin mandar `previous_bout_id` — lo deriva el backend, E4).
- [ ] **Mis Alertas**: suscripciones activas (botón cancelar) + historial desde `GET /api/alerts`.
- [ ] **Ajustes**: timezone, estado de permisos, botón "Probar alarma" → `POST /api/devices/me/test-alarm`, info diagnóstico FCM.
- [ ] **AlarmScreen** (modal full-screen): "McGregor vs Holloway — UFC 329 empieza en ~15 min" + botón "Descartar" (para el sonido). Se abre desde el `AlarmReceiver` vía `AlarmActivity`.

**Diseño y estado:**
- [ ] Design tokens: Inter (fuente), rojo UFC `#E50914`, fondo oscuro `#0A0A0A` (reusados de la web D35/D36).
- [ ] Estado server: TanStack Query. `device_id` en `expo-secure-store`.
- [ ] Tests: Jest + React Native Testing Library (pantallas principales + `AlarmScheduler`).
- [ ] Validar en emulador: navegación, API, pantallas, flujo completo crear/cancelar alerta, verify-then-ring, Doze (`dumpsys deviceidle force-idle`).
- [ ] **Confirmación en móvil físico**: bypass-silent con `setAlarmClock` (D40) + OEM quirks.

### Fase 7c — Deploy + smoke real

- [ ] Backend en Railway (D33) con env-vars: `FCM_CREDENTIALS`, `FCM_PROJECT_ID`.
- [ ] Firebase project + `google-services.json` en EAS.
- [ ] Build EAS free tier → APK interno para el owner.
- [ ] Smoke: crear alerta, verificar que la alarma local suena en hardware Android físico con DnD/silencio.

### Fase 7d — iOS (post-MVP, D40 vía AlarmKit)

- [ ] Mismo código Expo con build iOS via EAS.
- [ ] **AlarmKit** (iOS 26+, WWDC25 sesión 230): `AlarmManager.schedule(id:configuration:)` con `Alarm.Schedule.fixed(date)`, título custom, sonido custom, botón secundario con App Intent para abrir la app. El sistema garantiza bypass de silencio y focus sin Critical Alert Entitlement — solo requiere `NSAlarmKitUsageDescription` en el plist y opt-in del usuario. Ciclo de vida completo: cancelar/reprogramar por id (mismo patrón que `setAlarmClock` en Android).
- [ ] Requisito mínimo iOS 26 (adopción mayoritaria esperada para cuando se ejecute esta fase). Sin fallback a Critical Alert — el entitlement es discrecional de Apple y lento.
- [ ] Mismo módulo conceptual `AlarmScheduler` con backend Swift nativo (módulo Expo custom o library de la comunidad si existe).



