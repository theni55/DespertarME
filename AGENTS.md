# Guía para LLMs y continuadores

**Antes de empezar a trabajar**, lee en este orden:

1. `memoria/handoff.md` — estado actual, qué se hizo en la última sesión, próximo paso.
2. `README.md` — contexto de la aplicación (qué resuelve, para quién).
3. `memoria/` — documentación viva del proyecto (índice abajo).

Este archivo (`AGENTS.md`) es la chuleta ejecutable: comandos, prerequisitos, reglas.

## Índice de memoria/

> Generado automáticamente por `scripts/gen_memoria_index.py`. **No editar a mano**
> entre los marcadores: el hook `pre-commit` lo regenera en cada commit.

<!-- MEMORIA-INDEX:START -->
| Documento | Descripción |
|-----------|-------------|
| [Handoff](memoria/handoff.md) | Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión. |
| [Contexto de la aplicación](memoria/contexto.md) | Visión del producto, caso de uso y alcance del avisador de alertas deportivas. |
| [Arquitectura](memoria/arquitectura.md) | Snapshot del diseño: diagrama de componentes, flujo de alerta, entidades y stack. |
| [Decisiones tomadas](memoria/decisiones.md) | Registro histórico de decisiones de diseño (D1–D23) y decisiones pendientes. No editar las históricas; añadir nuevas con justificación. |
| [Fuentes de datos (investigación)](memoria/fuentes-datos.md) | Fuentes por deporte, hallazgos verificados de ESPN Core API y tareas de validación pendientes. |
| [Fases de implementación](memoria/fases.md) | Roadmap por fases con checkboxes. Marca los sub-items al completarlos y refleja el avance en handoff.md. |
| [Convenciones del proyecto](memoria/convenciones.md) | Reglas de código, commits, testing y estilo que todo continuador debe respetar. |
| [Bitácora de sesiones](memoria/bitacora.md) | Registro cronológico de cada sesión de trabajo: qué se hizo y qué quedó pendiente. |
| [Plan MVP visual + funcional — App Android (para Fable 5)](memoria/plan-mvp-android-fable5.md) | Plan por fases con checkboxes para completar un MVP visual y funcional de la app Android (Kotlin/Compose) en `mobile-kotlin/`, pensado para cargarlo en Fable 5 vía `/goal`. |
| [Plan MVP iOS + cierre Android — dogfooding personal](memoria/plan-mvp-ios.md) | Plan para estabilizar el MVP Android en el dispositivo del compañero y arrancar el MVP iOS (owner), antes de plantear publicación. Complementa `plan-mvp-android-fable5.md` (ese cubre solo Android). |
<!-- MEMORIA-INDEX:END -->

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
| Regenerar índice memoria | `python scripts/gen_memoria_index.py` |
| Verificar índice (CI/hook) | `python scripts/gen_memoria_index.py --check` |
| Activar hooks git | `pwsh scripts/setup-hooks.ps1` |
| Logs Postgres | `docker compose logs -f postgres` |
| Logs Redis | `docker compose logs -f redis` |
| Parar infra | `docker compose down` |
| Borrar volúmenes | `docker compose down -v` (¡borra datos!) |

## Endpoints

- `GET /health` → `{"status":"ok","env":"development"}`
- `GET /` → info del proyecto
- `GET /docs` → Swagger UI (FastAPI auto)

## Estructura de carpetas

```
DespertarME/
├─ README.md              # contexto de la aplicación (qué + por qué)
├─ AGENTS.md              # esta chuleta (comandos + índice de memoria/)
├─ memoria/               # documentación viva (ver índice arriba)
├─ scripts/               # utilidades (índice de memoria, hooks, probe ESPN)
├─ .githooks/             # hooks git versionados (pre-commit)
├─ pyproject.toml · .env.example · docker-compose.yml · Dockerfile
├─ alembic/               # migraciones
├─ src/app/               # código (main, config, db, providers, engine, notifiers, api, web)
└─ tests/                 # pytest + fixtures
```

## Memoria viva y hooks

La documentación de proyecto vive en `memoria/` (índice arriba). Reglas:

- **Cada `memoria/*.md`** empieza con un `# Título` y una línea `> descripción`
  (usada por el generador del índice).
- **El índice de arriba se autogenera**: no lo edites a mano. Corre
  `python scripts/gen_memoria_index.py` o deja que el hook lo haga.
- **Hook `pre-commit`** (`.githooks/pre-commit`), se activa con
  `pwsh scripts/setup-hooks.ps1` (una vez por clon). En cada commit:
  1. Regenera el índice de `memoria/` en `AGENTS.md` y lo re-stagea.
  2. Si detecta **cambios significativos** (en `src/`, `alembic/`, `pyproject.toml`,
     `docker-compose.yml`) sin tocar `memoria/handoff.md`, **aborta el commit**
     con un aviso. Salta el aviso puntualmente con `git commit --no-verify`.

## Reglas al continuar el trabajo

1. Lee `memoria/handoff.md` primero para saber dónde se quedó y qué sigue.
2. Lee el README (contexto) y los módulos de `memoria/` relevantes.
3. **No modifiques** decisiones ya tomadas en `memoria/decisiones.md` (D1-D23...).
   Si necesitas cambiar una, añade una nueva `D{n}` con justificación.
4. Marca los checkboxes en `memoria/fases.md` al completar sub-items.
5. Añade entrada en `memoria/bitacora.md` al final de cada sesión.
6. Actualiza `memoria/handoff.md` con el nuevo estado al final de cada sesión.
7. Código en inglés, docs y comentarios en español.
8. Type hints obligatorios. Solo comentarios "por qué" no-trivial.
9. Antes de cada commit pasa: `ruff check`, `black --check`, `pytest`.
10. Si necesidades de red te bloquean (API no accesible, sin Python/Docker),
    pregunta al usuario antes de inventar o saltarte pasos.