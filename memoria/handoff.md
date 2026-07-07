# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

## Última sesión

**Fecha:** 2026-07-07 · **Sesión 3**

**Qué se hizo:**
- Modularizada la documentación en `memoria/` (contexto, arquitectura, decisiones,
  fuentes-datos, fases, convenciones, bitácora, handoff).
- README simplificado a solo el contexto de la aplicación.
- Índice de `memoria/` auto-generado en `AGENTS.md` vía `scripts/gen_memoria_index.py`.
- Hook `pre-commit` que regenera el índice y avisa si hay cambios significativos
  sin actualizar este `handoff.md`.

**Commits/ramas:** rama `dev` en `theni55/DespertarME`.

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

Detalle de checkboxes en `fases.md`.

---

## Próximo paso — Fase 0 (Providers ESPN + tests)

1. Interfaz `Provider` (`src/app/providers/base.py`):
   `list_upcoming_events`, `get_event_card`, `get_competition_status`.
2. `espn_ufc.py` con httpx async + backoff + circuit breaker (D20).
3. Fixtures JSON en `tests/fixtures/espn_ufc/`.
4. Tests con `respx` en `tests/test_espn_ufc.py`.
5. Script `scripts/probe_espn.py` (smoke manual).

---

## Notas de entorno

- **Python**: 3.12.10. venv en `.venv` → activar `.\.venv\Scripts\Activate.ps1`.
- **Docker Desktop**: instalado; puede requerir reinicio de Windows. No bloqueante
  para Fase 0 (tests con respx, sin BD/Redis).
- **Postgres + Redis**: no arrancados aún (`docker compose up -d` + `alembic
  upgrade head` para Fase 2b+).
- **FastAPI**: `uvicorn app.main:app --reload` funciona sin BD/Redis.
- **Hooks git**: activar una vez con `pwsh scripts/setup-hooks.ps1` (o
  `git config core.hooksPath .githooks`).

---

## Comandos quick-start

```powershell
.\.venv\Scripts\Activate.ps1     # activar venv
uvicorn app.main:app --reload     # servidor dev
pytest -v                          # tests
ruff check src tests               # lint
python scripts/gen_memoria_index.py  # regenerar índice en AGENTS.md
```
