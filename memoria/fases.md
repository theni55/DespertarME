# Fases de implementación

> Roadmap por fases con checkboxes. Marca los sub-items al completarlos y refleja el avance en handoff.md.

## Fase 0 — Providers ESPN UFC + tests (próximo paso)

- [ ] Interfaz `Provider` (`base.py`) con `list_upcoming_events`, `get_event_card`, `get_competition_status`
- [ ] Implementación `espn_ufc.py` con httpx async + backoff exponencial con jitter (D20) + circuit breaker (D20)
- [ ] **Fixtures JSON grabadas** en `tests/fixtures/espn_ufc/`: event_list.json, event_600059148.json, competition_status_pre.json, competition_status_in.json, competition_status_post.json
- [ ] Tests unitarios en `tests/test_espn_ufc.py` con `respx` (mock httpx):
  - [ ] Listar eventos devuelve lista no vacía.
  - [ ] Detalle evento devuelve los 14 combates con `matchNumber` ordenado y `cardSegment`.
  - [ ] Parser de `status.type.state` distingue `pre`/`in`/`post`.
  - [ ] Backoff retry en 429/5xx.
  - [ ] Circuit breaker abre tras N fallos consecutivos.
- [ ] Script runnable `scripts/probe_espn.py` (smoke manual: próximo evento + número de combates).
- [ ] Validación: alta del atleta para mostrar nombre en alerta.

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

## Fase 2a — EstimatorEngine puro

- [ ] `domain/entities.py` (Bout, Card, EstimatedStart, Subscription)
- [ ] `engine/estimator.py` con lógica pura de recálculo:
  - [ ] transición `pre → in` del combate previo → estimación por duración media.
  - [ ] transición `in → post` del combate previo → `start = now + buffer_intercombate` (D18).
  - [ ] regla "X minutos antes" configurable por suscripción.
- [ ] **Tests aislados** con reloj fake (`freezegun`) y provider fake; sin Redis, sin BD.

## Fase 2b — Poller + idempotencia

- [ ] `engine/state.py` con Redis (registro de alertas ya disparadas): `SET alert:{sid}:{bid}:{status} 1 EX {ttl}` (D16).
- [ ] `engine/poller.py` con APScheduler async + cadencia adaptativa D15 (60/10/5 s).
- [ ] `notifiers/dummy.py` (log-only) para validar sin llamadas reales.
- [ ] `notifiers/base.py` con interfaz `VoiceNotifier`.
- [ ] Modelos BD mínimos: `users`, `bout_subscriptions`, `alert_log` con UNIQUE constraint `(subscription_id, bout_id, fired_at_hour)` (D16).
- [ ] Reintentos 1 s/5 s/30 s con backoff (D17).
- [ ] **Tests end-to-end** simulando transiciones de estado del combate previo.

## Fase 3 — Multiusuario + admin web

- [ ] Esquema BD completo + migraciones Alembic (extiende lo de Fase 2b).
- [ ] Auth JWT (registro / login / refresh).
- [ ] API REST: users, subscriptions, alert_log (CRUD).
- [ ] Panel admin Jinja2 + HTMX (D21).
- [ ] Tests de integración API + BD test.

## Fase 4 — Boxeo/Tenis reales (fuera del MVP)

- [ ] Implementar `scrap_tennis.py` (flashscore/tennistemple) si ampliamos a tenis.
- [ ] Boxeo: integrar si TheSportsDB o ESPN cubren la card ordenada.
- [ ] Bellator/PFL: usar TheSportsDB (D12).
- [ ] Tests con HTML fixtures grabados.

## Fase 5 — VoiceNotifier real

- [ ] Implementar `TwilioNotifier` (D23) con `twilio` SDK.
- [ ] Plantilla TTS del mensaje: "Tu combate X vs Y comenzará en breve, por la tarjeta de UFC XXX".
- [ ] Tests con mocks de la API de Twilio.
