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

## Fase 7 — App móvil Android (React Native + Expo) 🔶 en planificación

### Fase 7a — Backend: device model + JSON endpoints + FCM notifier

- [ ] Decisión D37 registrada en `decisiones.md`.
- [ ] Nuevo modelo `Device` (`id`, `fcm_token`, `platform`, `timezone`, `locale`, `created_at`, `last_seen_at`, `is_active`) + migración Alembic.
- [ ] `BoutSubscription` y `AlertLog`: añadir `device_id` nullable (FK a `devices`), sin romper histórico con `user_id`.
- [ ] Endpoints `/api/devices` (register con FCM token + timezone + platform → device_id UUID; unregister).
- [ ] Auth device: dependencia `get_current_device` vía header `X-Device-Id`.
- [ ] Exponer ESPN como JSON: `GET /api/events` (lista) + `GET /api/events/{id}` (tarjeta con bouts + `AthleteResolver` para fotos/nombres). Reutiliza lógica de `web/user.py`.
- [ ] `notifiers/fcm.py` con `firebase-admin`: mensaje data-only `{type: "alarm", event, bout, fighters, starts_in_min}`. `build_notifier()` gated por `FCM_CREDENTIALS` env-var → `DummyNotifier` si no configurado.
- [ ] `Poller` refactorizado: carga `Device` (fcm_token, timezone) en vez de `User.phone`. Skip dispositivos inactivos.
- [ ] Admin web refactorizado: vista de devices (FCM token ofuscado) + sus suscripciones + log de alertas. Quitar gestión de usuarios.
- [ ] Tests: device register/unregister, FCM notifier mocked, poller con device, eventos JSON. Mantener tests existentes verdes.
- [ ] Verificación: `ruff`/`black`/`mypy`/`pytest` + smoke con `httpx`/`curl`.

### Fase 7b — App Android v1 (Expo + React Native)

- [ ] Setup: `create-expo-app` con TypeScript + Expo Router + EAS config. Dev build (prebuild) — no Expo Go. Carpeta `mobile/` en raíz del repo.
- [ ] Spike de alarma: validar que FCM high-priority → notification channel `IMPORTANCE_HIGH` + `setBypassDnd(true)` + foreground service `STREAM_ALARM` suena con el teléfono en silencio. **Primer milestone antes de construir pantallas.**
- [ ] Native module Android (Kotlin): `AlarmNotificationsModule` (crea channel) + `AlarmService` (foreground, `MediaPlayer.STREAM_ALARM`, looping) + `AlarmActivity` (full-screen intent sobre lockscreen con `setShowWhenLocked`/`setTurnScreenOn`).
- [ ] Permisos AndroidManifest: `USE_FULL_SCREEN_INTENT`, `SCHEDULE_EXACT_ALARM`, `FOREGROUND_SERVICE`, `POST_NOTIFICATIONS`, `RECEIVE_BOOT_COMPLETED`, `WAKE_LOCK`, `VIBRATE`.
- [ ] Cliente FCM: `@reactnative-firebase/messaging`. Handler background → lanza `AlarmService`. Handler foreground → abre `AlarmScreen`.
- [ ] Pantalla Home: cabecera marca, botón grande "Avísame" → navega a Eventos.
- [ ] Pantalla Eventos: lista de próximos UFC (card con imagen, fecha, main event) desde `GET /api/events`.
- [ ] Pantalla EventDetail: tarjeta de combates (matchNumber, segmento, foto+nombre peleadores con borde rojo/azul), selector de minutos (5/10/15/30), botón "Avisarme" → `POST /api/subscriptions`.
- [ ] Pantalla Mis Alertas: suscripciones activas (cancelar) + historial desde `GET /api/alerts`.
- [ ] Pantalla Ajustes: timezone, estado de permisos (re-pedir bypass DnD), diagnóstico FCM.
- [ ] AlarmScreen (modal full-screen): "El combate X vs Y de UFC N empieza en N min" + botón "Descartar" (para el sonido).
- [ ] Estado server: TanStack Query. Persistencia: AsyncStorage para `device_id`.
- [ ] Diseño: design tokens alineados con la web (Inter Variable, paleta rojo UFC). Skills: `frontend-ui-engineering` + `ship-polished-ui` (cuando se cree).
- [ ] Tests: Jest + React Native Testing Library para pantallas principales.
- [ ] Build: EAS Build Android → APK/AAB internal. Prueba en dispositivo físico real (el "suene en silencio" solo se valida en hardware).

### Fase 7c — Deploy + smoke real

- [ ] Backend en Railway (D33) con env-vars: `FCM_CREDENTIALS`, `FCM_PROJECT_ID`.
- [ ] Proyecto Firebase + app Android + `google-services.json` cargado en EAS.
- [ ] APK al owner → prueba en su móvil con teléfono en silencio: crear alerta, disparar desde backend, verificar alarma.
- [ ] Iterar ajustes.

### Fase 7d — iOS (post-MVP, tras validar Android)

- [ ] Mismo código Expo con build iOS via EAS.
- [ ] Solicitar **Critical Alert Entitlement** de Apple (justificación: avisos urgentes de eventos deportivos en tiempo real).
- [ ] Sin entitlement, iOS no bypass silent — decidir con el owner si aceptar limitación o esperar aprobación.



