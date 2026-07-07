# Handoff — Sesión 3

> **Actualizar al final de cada sesión.** Este archivo es el punto de entrada para
> cualquier LLM o persona que retome el proyecto. Complementa al README (fuente de
> verdad) con el estado operativo actual.

---

## Última sesión

**Fecha:** 2026-07-07

**Qué se hizo:**
- Clonado el repo en `C:\Users\javier.romero\Personal\DespertarME`.
- Creado directorio `memoria/` con `arquitectura.md` (snapshot de diseño) y este `handoff.md`.
- Actualizados `AGENTS.md` y `README.md` para referenciar `memoria/`.

**Commits:** _pendiente de commit_

---

## Estado global

| Fase | Estado |
|------|--------|
| Fase 0 — Providers ESPN + tests | **Pendiente** (próximo paso) |
| Fase 1 — Scaffold | **Completada** |
| Fase 2a — EstimatorEngine puro | Pendiente |
| Fase 2b — Poller + idempotencia | Pendiente |
| Fase 3 — Multiusuario + admin web | Pendiente |
| Fase 4 — Boxeo/Tenis reales | Pendiente (fuera del MVP) |
| Fase 5 — VoiceNotifier real (Twilio) | Pendiente (fuera del MVP) |

---

## Próximo paso

**Fase 0 — Providers ESPN + tests:**

1. Crear interfaz `Provider` (`src/app/providers/base.py`):
   - `list_upcoming_events`, `get_event_card`, `get_competition_status`
2. Implementar `espn_ufc.py` con httpx async + backoff + circuit breaker (D20).
3. Grabar fixtures JSON en `tests/fixtures/espn_ufc/`:
   - `event_list.json`, `event_600059148.json`, `competition_status_pre.json`,
     `competition_status_in.json`, `competition_status_post.json`
4. Tests unitarios con `respx` en `tests/test_espn_ufc.py`.
5. Script `scripts/probe_espn.py` (smoke manual).

---

## Notas de entorno

- **Python**: 3.12.10 en `C:\Users\pacor\AppData\Local\Programs\Python\Python312\`
- **venv**: `.venv` ya creado. Activar: `.\.venv\Scripts\Activate.ps1`
- **Docker Desktop**: instalado pero puede requerir reinicio de Windows para
  arrancar el daemon. No es bloqueante para Fase 0 (solo tests unitarios con
  respx, sin BD/Redis).
- **Postgres + Redis**: no arrancados aún. `docker compose up -d` + `alembic
  upgrade head` pendientes para Fase 2b+.
- **FastAPI**: `uvicorn app.main:app --reload` funciona sin BD/Redis.
  `/health` responde `{"status":"ok","env":"development"}`.

---

## Comandos quick-start

```powershell
# Activar venv
.\.venv\Scripts\Activate.ps1

# Servidor dev
uvicorn app.main:app --reload

# Tests
pytest -v

# Lint + formato
ruff check src tests
black --check src tests
mypy src/app

# Infraestructura (cuando Docker esté listo)
docker compose up -d
alembic upgrade head

# Smoke ESPN (Fase 0)
python scripts/probe_espn.py
```
