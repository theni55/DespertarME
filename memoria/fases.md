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
