# Guía para LLMs y continuadores

**Antes de empezar a trabajar**, lee en este orden:

1. `memoria/handoff.md` — estado actual, qué se hizo en la última sesión, próximo paso.
2. `README.md` — fuente de verdad del proyecto (decisiones, fases, bitácora).
3. `memoria/arquitectura.md` — snapshot del diseño (diagrama, flujo, entidades, stack).

Este archivo (`AGENTS.md`) es la chuleta ejecutable: comandos, prerequisitos, reglas.

## Prerequisitos

- Python 3.12+ instalado y en PATH.
- Docker Desktop corriendo (para Postgres + Redis locales). Si el daemon de
  Docker no está levantado, la app aún arranca pero no podrá acceder a BD/Redis.

## Setup inicial (una sola vez)

```powershell
# 1. Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar el proyecto en modo editable con deps de desarrollo
pip install --editable .[dev]

# 3. Copiar .env
Copy-Item .env.example .env
# -> edita .env con tus secretos (no se sube a git)

# 4. Levantar infraestructura (Postgres + Redis)
docker compose up -d

# 5. Aplicar migraciones
alembic upgrade head
```

## Comandos frecuentes

| Acción | Comando |
|--------|---------|
| Servidor dev | `uvicorn app.main:app --reload` |
| Tests | `pytest` |
| Tests verbose | `pytest -v` |
| Un test | `pytest tests/test_health.py -v` |
| Lint | `ruff check src tests` |
| Lint fix | `ruff check --fix src tests` |
| Formato | `black src tests` |
| Type check | `mypy src/app` |
| Migración nueva | `alembic revision --autogenerate -m "desc"` |
| Aplicar migraciones | `alembic upgrade head` |
| Bajar migración | `alembic downgrade -1` |
| Smoke ESPN (Fase 0) | `python scripts/probe_espn.py` |
| Logs Postgres | `docker compose logs -f postgres` |
| Logs Redis | `docker compose logs -f redis` |
| Parar infra | `docker compose down` |
| Borrar volúmenes | `docker compose down -v` (¡borra datos!) |

## Endpoints

- `GET /health` → `{"status":"ok","env":"development"}`
- `GET /` → info del proyecto
- `GET /docs` → Swagger UI (FastAPI auto)

## Estructura de carpetas

Ver sección "Estructura de carpetas prevista" del README.

## Reglas al continuar el trabajo

1. Lee `memoria/handoff.md` primero para saber dónde se quedó y qué sigue.
2. Lee el README completo (estado actual + decisiones + bitácora).
3. **No modifiques** decisiones ya tomadas (D1-D23...). Si necesitas cambiar
   una, añade una nueva decisión `D{n}` con justificación.
4. Marca los checkboxes al completar sub-items de una fase.
5. Añade entrada en la bitácora del README al final de cada sesión.
6. Actualiza `memoria/handoff.md` con el nuevo estado al final de cada sesión.
7. Código en inglés, docs y comentarios en español.
8. Type hints obligatorios. Solo comentarios "por qué" no-trivial.
9. Antes de cada commit pasa: `ruff check`, `black --check`, `pytest`.
10. Si necesidades de red te bloquean (API no accesible, sin Python/Docker),
    pregunta al usuario antes de inventar o saltarte pasos.