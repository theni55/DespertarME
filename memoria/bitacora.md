# Bitácora de sesiones

> Registro cronológico de cada sesión de trabajo: qué se hizo y qué quedó pendiente.

## Sesión 1 — Inicio del proyecto

- Recogida de requisitos con el usuario vía preguntas estructuradas.
- Investigación de fuentes de datos gratuitas para MMA/Boxeo/Tenis.
- Definición de stack (Python + FastAPI + APScheduler + Postgres + Redis) — decisiones D1-D8.
- Definición de arquitectura pluggable por deporte (D3).
- Creación del README como documento vivo (D8).
- **Pendiente**: confirmar Fase 1 y arrancar trabajo.

## Sesión 2 — Decisiones de diseño + Fase 1 scaffold completada

- **Verificación en vivo de APIs**: ESPN `site.api.espn.com` devolvía 404; ESPN
  `sports.core.api.espn.com/v2` funciona con datos reales (UFC 329, 14 combates,
  statuses). TheSportsDB sin tarjeta útil. ufcstats.com no conecta.
- Nuevas decisiones **D9–D23** (ver `decisiones.md`).
- **Reordenación de fases**: Fase 0 = providers ESPN + tests; Fase 1 = scaffold;
  Fase 2 dividida en 2a (estimador puro) y 2b (poller + idempotencia).
- **Instalación de entorno via winget**: Python 3.12.10 + Docker Desktop.
- **Fase 1 (Scaffold) completada**: estructura de archivos, `pyproject.toml`,
  Docker compose, Dockerfile, FastAPI mínimo con `/health` y `/`, `config.py`,
  `db/session.py` async, Alembic con migración `0001`, `AGENTS.md`, tests.
- **Verificación funcional**: `pip install -e .[dev]` OK · `pytest` 2/2 · `ruff`
  OK · `black` OK · uvicorn levanta y `/health` responde.
- **Pendiente**: activar Docker, arrancar Fase 0 (providers ESPN + tests).

## Sesión 3 — Directorio memoria + modularización de docs

- Clonado el repo en `C:\Users\javier.romero\Personal\DespertarME`.
- Creado directorio `memoria/` con módulos: `contexto`, `arquitectura`,
  `decisiones`, `fuentes-datos`, `fases`, `convenciones`, `bitacora`, `handoff`.
- **README simplificado** a solo el contexto de la aplicación; el detalle vive
  ahora en `memoria/`.
- **Índice auto-generado** en `AGENTS.md` entre marcadores vía
  `scripts/gen_memoria_index.py`.
- **Hook `pre-commit`** (`.githooks/pre-commit`) que regenera el índice y avisa
  si hay cambios significativos sin actualizar `handoff.md`.
- Rama `dev` en `theni55/DespertarME` (repo compartido, colaboración por PR).
- **Pendiente**: Fase 0 — Providers ESPN + tests.

## Sesión 4 — Fase 0 completada (Providers ESPN UFC + tests)

- **Fixtures grabados en vivo** en `tests/fixtures/espn_ufc/`: `event_list.json`,
  `event_600059148.json` (UFC 329, 14 combates, todos `pre`), y los 3 estados
  `competition_status_pre.json` / `_in.json` / `_post.json` (estos dos últimos
  sintetizados a partir del esquema real porque no había eventos `in`/`post` en
  la temporada 2026 al grabar).
- **Interfaz `Provider`** (`src/app/providers/base.py`) como ABC con 3 métodos
  async: `list_upcoming_events`, `get_event_card`, `get_competition_status`.
- **DTOs** en `src/app/providers/models.py` (pydantic, `extra="ignore"`):
  `AthleteRef`, `Competitor`, `CardSegment`, `BoutFormat`, `WeightClass`,
  `Bout`, `CompetitionStatus`, `EventSummary`, `Event`.
- **`EspnUfcProvider`** en `src/app/providers/espn_ufc.py`: httpx async +
  `tenacity` (backoff exponencial con jitter 1→60 s, retry en 429/5xx y
  `TransportError`) + circuit breaker manual (N fallos consecutivos → open,
  `clock` inyectable para tests). Decisión **D24** registrada.
- **Dep añadida**: `tenacity>=8.4` en `pyproject.toml`.
- **Tests** en `tests/test_espn_ufc.py` con `respx`: 10 tests cubren los 5
  items del checklist (listar, 14 combates ordenados, estados pre/in/post,
  backoff en 429/5xx, 4xx sin retry, CB abre tras N fallos, CB reset).
- **`scripts/probe_espn.py`** smoke manual: verificado en vivo contra ESPN
  (1 evento, 14 combates, segmentos prelims2/prelims1/main, estado `pre`).
- **Verificación completa**: `pytest` 12/12 ✅ · `ruff check` ✅ ·
  `black --check` ✅ · `mypy src/app` ✅.
- **Pendiente**: validación en vivo del estado `in`/`post` cuando haya un
  combate en curso; resolver `$ref` de atleta para nombre en alerta (Fase 3/5).

## Sesión 4 (cont.) — Fases 2a, 2b y 3 completadas

- **Fase 2a (EstimatorEngine puro)**:
  - `src/app/domain/entities.py`: dataclasses frozen (`Athlete`, `Bout`, `Card`,
    `BoutStatus`, `EstimatedStart`, `Subscription`). `Bout.estimated_duration_seconds`
    = rounds*300 + (rounds-1)*60.
  - `src/app/engine/estimator.py`: `EstimatorEngine.estimate()` recalcúa inicio
    según estado del combate previo (pre → fecha programada; in → now +
    remaining + buffer; post → now + buffer D18). `poll_interval()` aplica D15.
  - 15 tests en `tests/test_estimator.py` con freezegun (sin Redis, sin BD).

- **Fase 2b (Poller + idempotencia)**:
  - Modelos BD en `src/app/db/models/`: `User`, `SportSubscription`,
    `EventSubscription`, `BoutSubscription`, `AlertLog` (con UNIQUE constraint
    D16). Migración Alembic `a3657c6166f0` generada y aplicada.
  - `src/app/notifiers/`: interfaz `VoiceNotifier` + `DummyNotifier` (log-only).
  - `src/app/engine/state.py`: `AlertState` con Redis (SETNX + EX, D16),
    `redis.Redis` inyectable (fakeredis en tests).
  - `src/app/engine/poller.py`: `Poller.poll_once()` orquesta
    provider→estimator→idempotencia→notifier→BD. Reintentos D17 (1/5/30 s,
    delays inyectables para tests). Decisión D29 (sin scheduler todavía).
  - 6 tests E2E en `tests/test_poller.py` con fakeredis + SQLite en memoria.
  - **Decisiones D25–D27** registradas.

- **Fase 3 (Multiusuario + admin web)**:
  - Auth JWT (`src/app/auth/`): passlib[bcrypt] + PyJWT, `get_current_user`/
    `require_admin` como dependencias. Decisión **D28**.
  - API REST (`src/app/api/routes/`): auth (register/login), users (admin),
    subscriptions (CRUD), alerts (list). Esquemas pydantic en `schemas.py`.
  - Panel admin web (`src/app/web/`): Jinja2 + HTMX (D21). Login con cookie,
    dashboard (contadores + alertas recientes), usuarios, log de alertas.
    Templates en `src/app/web/templates/` (dark mode, responsive).
  - 13 tests de integración en `tests/test_api.py` con TestClient + BD override.
  - **Deps añadidas**: `passlib[bcrypt]`, `bcrypt<5.0`, `pyjwt`, `jinja2`,
    `python-multipart`, `pydantic[email]`; dev: `aiosqlite`, `fakeredis`.

- **Infra**: Docker Desktop no arranca → SQLite + aiosqlite (dev BD) +
  fakeredis (tests). `.env` cambiado a `sqlite+aiosqlite:///./avisador.db`.

- **Verificación final**: `pytest` 46/46 ✅ · `ruff check` ✅ ·
  `black --check` ✅ · `mypy src/app` ✅ · servidor levanta OK
  (`/health`, `/admin/login`, `/docs` responden).

- **Pendiente**: APScheduler real que llame a `poll_once` periódicamente;
  integrar admin web con crear-usuario-admin seed; resolver `$ref` de atleta.

## Sesión 4 (cont. 2) — Web de usuario funcional

- El usuario reportó que la Fase 3 entregada solo tenía panel admin
  (estadísticas) pero no vista funcional de usuario para ver eventos y crear
  alertas. Reconocido: la Fase 3 decía "admin web" literal pero el alcance
  implícito (`contexto.md:28` "frontend de administración web") incluía la
  vista de usuario.
- **Construido `src/app/web/user.py`** (router `/app/*`):
  - Registro y login de usuario (form POST → cookie JWT).
  - Dashboard: eventos próximos (ESPN en vivo) + suscripciones activas + alertas recientes.
  - `/app/events`: lista de eventos UFC desde `EspnUfcProvider.list_upcoming_events()`.
  - `/app/events/{id}`: tarjeta de combates ordenada con matchNumber, segmento,
    categoría de peso, rounds, y botón "Avisar" con campo de minutos configurables.
  - `/app/subscriptions/create`: crea alerta autodetectando el combate previo
    (matchNumber+1) desde la tarjeta ESPN.
  - `/app/subscriptions/{id}/delete`: cancela suscripción (soft delete → `cancelled`).
  - `/app/my-alerts`: historial de alertas del usuario.
- **7 templates nuevos**: `user_register`, `user_login`, `user_dashboard`,
  `event_list`, `event_detail`, `my_alerts` (+ `base.html` reutilizado).
- **`/` ahora redirige a `/app`** (entrada directa a la vista de usuario).
- **`scripts/seed_admin.py`**: crea usuario admin de prueba.
- **Verificación**: 50/50 tests ✅ · ruff ✅ · black ✅ · mypy ✅ ·
  flujo completo verificado con httpx (registro → dashboard → eventos →
  detalle → crear alerta → verla activa → cancelar).
