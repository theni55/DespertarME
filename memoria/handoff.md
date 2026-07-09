# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

## Última sesión

**Fecha:** 2026-07-09 · **Sesión 5 (MVP launch)**

**Qué se hizo:**
- **Peleadores con cara y nombre** en la tarjeta: `get_athlete()` + `AthleteResolver`
  (caché Redis 7d + memoria, D32) + `event_detail.html` rediseñada. Verificado en
  vivo: 28 headshots + nombres reales.
- **TwilioNotifier** (TwiML inline es-ES, D30) **gated por config**: sin las 3
  env-vars de Twilio usa `DummyNotifier`. Se activa sin tocar código.
- **Poller con datos reales**: teléfono del usuario, nombres de peleadores y
  evento en el payload; salta usuarios sin teléfono/inactivos.
- **Scheduler in-process** (APScheduler en lifespan, D31): `poll_once` cada 60 s.
  Requisito: 1 worker uvicorn. `SCHEDULER_ENABLED=false` para desactivar.
- **Teléfono obligatorio E.164** en registro web + API (D34).
- **Admin detalle usuario**: `/admin/users/{id}` + activar/desactivar.
- **Preparación Railway** (D33): `railway.json`, Dockerfile prod, normalización
  `DATABASE_URL`, guard `JWT_SECRET` en producción.

**Verificación:** `pytest` 72/72 ✅ · `ruff` ✅ · `black` ✅ · `mypy` ✅ · smoke
E2E en vivo (registro → eventos → detalle con fotos) ✅ · scheduler arranca ✅.

**Commits/ramas:** rama `feature/mvp-launch` → PR a `main`.

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
| Fase 5 — VoiceNotifier real (Twilio) | **Completada** ✅ (falta cuenta Twilio para llamada real) |

Detalle de checkboxes en `fases.md`.

---

## Próximos pasos

1. **Deploy en Railway** (requiere cuenta del owner):
   - Crear proyecto desde el repo GitHub (`railway.json` ya configura build/start).
   - Añadir add-ons **Postgres** y **Redis** → Railway inyecta `DATABASE_URL` y
     `REDIS_URL` (la config normaliza el driver automáticamente).
   - Env-vars: `APP_ENV=production`, `JWT_SECRET` (generar con
     `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
   - Verificar `/health` y el dominio HTTPS que asigna Railway.
2. **Cuenta Twilio**: al tenerla, set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
   `TWILIO_FROM_NUMBER` en Railway → llamadas reales sin tocar código. Con
   cuenta trial solo llama a números verificados.
3. **Seguridad**: rotar el token GitHub embebido en el remote del clon local y
   pasar a credential helper.
4. (Opcional) Cadencia adaptativa D15 en el scheduler; CI GitHub Actions;
   resolver nombres también en dashboard/mis-alertas.

---

## Cómo levantar la web en local

```powershell
.\.venv\Scripts\Activate.ps1
# .env: DATABASE_URL=sqlite+aiosqlite:///./avisador.db (append tras copiar .env.example)
alembic upgrade head          # crea las tablas en avisador.db
uvicorn app.main:app --reload
```

**Usuario (vista funcional):**
- `http://localhost:8000/` → redirige a `/app` (login/registro de usuario)
- `http://localhost:8000/app/events/{event_id}` → tarjeta con fotos y nombres + crear alerta

**Admin:**
- `http://localhost:8000/admin/login` (seed: `python scripts/seed_admin.py`)
- `http://localhost:8000/admin/users/{id}` → detalle de usuario
- `http://localhost:8000/docs` → Swagger UI

---

## Notas de entorno

- **Python**: el `python` del PATH es 3.11; usar `py -3.12`. venv en `.venv`.
- **Redis local**: no es necesario para la web (la caché de atletas degrada a
  memoria); sí para idempotencia del Poller en producción.
- **Scheduler**: arranca con la app; en local sin Redis el poll loguea errores
  benignos si hay suscripciones activas. `SCHEDULER_ENABLED=false` para apagarlo.
- **Tip (PowerShell)**: usar `python -m pip` en vez de `pip`.
- **Hooks git**: activar una vez con `pwsh scripts/setup-hooks.ps1`.

---

## Comandos quick-start

```powershell
.\.venv\Scripts\Activate.ps1        # activar venv
alembic upgrade head                # aplicar migraciones (SQLite)
uvicorn app.main:app --reload        # servidor dev (API + web + scheduler)
pytest -v                            # tests (72)
python scripts/probe_espn.py          # smoke ESPN en vivo
ruff check src tests                  # lint
black --check src tests scripts       # formato
mypy src/app                          # type check
python scripts/gen_memoria_index.py   # regenerar índice en AGENTS.md
```
