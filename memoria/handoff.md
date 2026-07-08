# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

## Última sesión

**Fecha:** 2026-07-08 · **Sesión 4 (cont.)**

**Qué se hizo:**
- **Fases 2a, 2b y 3 completadas** en una sola sesión.
- **Fase 2a**: `domain/entities.py` (dataclasses frozen) + `engine/estimator.py`
  (recálculo puro según estado del combate previo). 15 tests con freezegun.
- **Fase 2b**: modelos BD (users, subscriptions, alert_log con UNIQUE D16) +
  migración Alembic aplicada + `notifiers/` (VoiceNotifier + DummyNotifier) +
  `engine/state.py` (Redis idempotencia) + `engine/poller.py` (orquestación +
  reintentos D17). 6 tests E2E con fakeredis + SQLite.
- **Fase 3**: Auth JWT (passlib + PyJWT) + API REST (auth/users/subscriptions/
  alerts) + panel admin Jinja2+HTMX (login, dashboard, usuarios, alertas).
  13 tests de integración con TestClient + BD override.
- **Infra**: Docker Desktop no arranca → SQLite+aiosqlite (dev) + fakeredis
  (tests). Decisiones **D25–D29** registradas.

**Verificación:** `pytest` 46/46 ✅ · `ruff` ✅ · `black --check` ✅ · `mypy` ✅ ·
servidor levanta OK (`/health`, `/admin/login`, `/docs` responden).

**Commits/ramas:** rama `dev` en `theni55/DespertarME` (sin commitear aún).

---

## Estado global

| Fase | Estado |
|------|--------|
| Fase 0 — Providers ESPN + tests | **Completada** ✅ |
| Fase 1 — Scaffold | **Completada** ✅ |
| Fase 2a — EstimatorEngine puro | **Completada** ✅ |
| Fase 2b — Poller + idempotencia | **Completada** ✅ |
| Fase 3 — Multiusuario + admin web | **Completada** ✅ |
| Fase 4 — Boxeo/Tenis reales | Pendiente (fuera del MVP) |
| Fase 5 — VoiceNotifier real (Twilio) | Pendiente (fuera del MVP) |

Detalle de checkboxes en `fases.md`.

---

## Próximos pasos

1. **APScheduler real**: integrar `poll_once` con un scheduler que respete la
   cadencia adaptativa D15 (`EstimatorEngine.poll_interval()`). D29 lo dejó
   pendiente.
2. **Seed de usuario admin** para poder entrar al panel web (`/admin/login`).
3. **Resolver `$ref` de atleta**: seguir la URL de `AthleteRef` para obtener
   el nombre y mostrarlo en el mensaje de alerta.
4. **Commit** de todo el trabajo de Fases 2a/2b/3 (sin commitear todavía).
5. (Opcional) CI de GitHub Actions (lint + tests).

Ver detalle en `fases.md` → Fase 4 y 5.

---

## Cómo levantar la web en local

```powershell
.\.venv\Scripts\Activate.ps1
# Asegurar que .env tiene DATABASE_URL=sqlite+aiosqlite:///./avisador.db
alembic upgrade head          # crea las tablas en avisador.db
uvicorn app.main:app --reload
```

**Usuario (vista funcional):**
- `http://localhost:8000/` → redirige a `/app` (login/registro de usuario)
- `http://localhost:8000/app` → dashboard del usuario (eventos + alertas activas)
- `http://localhost:8000/app/events` → eventos UFC próximos
- `http://localhost:8000/app/events/{event_id}` → tarjeta de combates + crear alerta
- `http://localhost:8000/app/my-alerts` → historial de alertas

**Admin (estadísticas):**
- `http://localhost:8000/admin/login` → login admin (seed: `admin@despertarme.com` / `admin123`)
- `http://localhost:8000/docs` → Swagger UI (API REST)

---

## Notas de entorno

- **Python**: 3.12.10. venv en `.venv` → activar `.\.venv\Scripts\Activate.ps1`.
- **Docker Desktop**: instalado pero no arranca. No bloqueante: BD en SQLite
  (`avisador.db`) y Redis solo se usa en el Poller (tests con fakeredis).
  Para producción: `docker compose up -d` + cambiar `DATABASE_URL` a `asyncpg`.
- **Tip (PowerShell)**: usar `python -m pip` en vez de `pip` (el alias `pip`
  no capturaba output en este entorno; `python -m pip` sí).
- **Hooks git**: activar una vez con `pwsh scripts/setup-hooks.ps1` (o
  `git config core.hooksPath .githooks`).

---

## Comandos quick-start

```powershell
.\.venv\Scripts\Activate.ps1        # activar venv
alembic upgrade head                # aplicar migraciones (SQLite)
uvicorn app.main:app --reload        # servidor dev (API + admin web)
pytest -v                            # tests (46)
python scripts/probe_espn.py          # smoke ESPN en vivo
ruff check src tests                  # lint
black --check src tests scripts       # formato
mypy src/app                          # type check
python scripts/gen_memoria_index.py   # regenerar índice en AGENTS.md
```
