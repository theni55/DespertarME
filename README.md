# Avisador de alertas deportivas en tiempo real

> **Documento vivo**: este README es la fuente de verdad del proyecto. Cualquier LLM o persona que continúe la tarea debe leerlo completo antes de empezar, y actualizarlo al final de cada sesión. Mantener la sección [Bitácora de sesiones](#bitácora-de-sesiones) y [Estado actual](#estado-actual) siempre al día.

---

## Índice

1. [Visión del producto](#visión-del-producto)
2. [Decisiones tomadas](#decisiones-tomadas)
3. [Decisiones pendientes](#decisiones-pendientes)
4. [Arquitectura](#arquitectura)
5. [Stack tecnológico](#stack-tecnológico)
6. [Fuente de datos (investigación)](#fuente-de-datos-investigación)
7. [Estructura de carpetas prevista](#estructura-de-carpetas-prevista)
8. [Fases de implementación](#fases-de-implementación)
9. [Estado actual](#estado-actual)
10. [Cómo continuar la tarea](#cómo-continuar-la-tarea)
11. [Convenciones del proyecto](#convenciones-del-proyecto)
12. [Bitácora de sesiones](#bitácora-de-sesiones)

---

## Visión del producto

Sistema de alertas telefónicas (llamada a SIM virtual) que avisa a un usuario **X minutos antes** de que empiece un combate/partido concreto de deportes con **tarjeta escalonada** (MMA, Boxeo, Tenis, etc.).

El problema que resuelve: en deportes como MMA el horario real de un combate depende de la duración de los combates anteriores de la tarjeta. El usuario quiereSer avisado cuando **el combate que le interesa vaya a empezar pronto**, lo cual requiere estimar el inicio en función del estado en vivo del combate anterior.

### Caso de uso típico
- Usuario subscribe: "Avísame 15 min antes del combate Main Card de UFC XXX entre X vs Y".
- Sistema sigue en vivo la tarjeta. Cuando el combate inmediatamente anterior termina (o está a punto de terminar), recalcula el inicio estimado del combate objetivo.
- Cuando `estimado - ahora ≤ 15 min` → dispara llamada telefónica al usuario.

### Alcance confirmado
- **Deportes prioritize**: MMA (UFC, Bellator) + Boxeo + Tenis/otros.
- **Canal de alerta**: llamada telefónica (sin SMS/Telegram de respaldo por ahora). Proveedor SIM virtual a decidir (Twilio/Vonage) — **no es prioritario aún**.
- **Usuarios**: multiusuario + frontend de administración web.
- **Tipo de alerta**: inicio inminente (X min antes, configurable por suscripción).

---

## Decisiones tomadas

| # | Decisión | Fecha | Justificación |
|---|----------|-------|---------------|
| D1 | Stack: Python + FastAPI + APScheduler + asyncio | Sesión 1 | Idóneo para polling, tareas programadas y multiusuario. |
| D2 | Postgres + Redis | Sesión 1 | Persistencia relacional + state temporal para el poller. |
| D3 | Providers pluggables por deporte (interfaz `Provider`) | Sesión 1 | Permite múltiples fuentes y scraping sin tocar el resto. |
| D4 | ESPN UFC (no-oficial) como fuente principal de MMA | Sesión 1 | Única gratuita con estado en vivo de cada combate de la card + orden. |
| D5 | TheSportsDB como fuente de Boxeo/MMA secundario | Sesión 1 | API gratuita con API key, eventos y scoreboard. |
| D6 | Scraping (flashscore/tennistemple) para Tenis en vivo | Sesión 1 | No existe API gratuita fiable con tiempo real de ATP/WTA. |
| D7 | `VoiceNotifier` como interfaz plug-in (Twilio/Vonage añadidos después) | Sesión 1 | Desacopla lógica de alerta del proveedor de llamadas. |
| D8 | README como documento vivo del proyecto | Sesión 1 | Permitir continuidad entre LLM/sesiones distintas. |
| D9 | **ESPN Core API** (`https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc/`) como única fuente para MMA/UFC. Sin auth. | Sesión 2 | Verificado en vivo: devuelve la tarjeta completa (14 combates) con `matchNumber` (orden), `cardSegment`, `format` y estado por combate. |
| D10 | TheSportsDB **excluido del MVP** para UFC. | Sesión 2 | Solo aporta metadata de evento, no combates individuales ni orden. ESPN ya cubre todo. |
| D11 | Scraping (ufcstats.com / tapology.com) **fuera del MVP**. | Sesión 2 | ESPN es fiable; ufcstats no conectó desde el entorno de prueba. Si ESPN fallase, se introduce como provider nuevo. |
| D12 | TheSportsDB se reserva para **Bellator/PFL** si se añaden después. | Sesión 2 | Ligas presentes en TheSportsDB aunque sin tarjetas; a estudiar cuando se amplíe alcance. |
| D13 | Endpoints ESPN confirmados: `/events?seasontype=2`, `/events/{id}`, `/events/{id}/competitions/{cId}/status`. | Sesión 2 | Cada uno verificado con HTTP 200 y payload real (UFC 329 McGregor vs Holloway 2). |
| D14 | Coste polling estimado: **2 req/suscripción/poll** (evento + status del combate anterior). | Sesión 2 | A 60 s/poll → ~2 req/min/suscripción; asumible dentro de rate-limit implícito de ESPN. |
| D15 | Cadencia de polling **adaptativa por estado**: 60 s default, 10 s cuando previo `in` avanzado, 5 s cuando previo `post`. | Sesión 2 | Equilibra precisión (más frecuencia justo cuando importa) y consumo (más relajada en reposo). |
| D16 | Idempotencia **defensa en profundidad**: clave Redis `alert:{subscription_id}:{bout_id}:{status_when_fired}` con TTL configurable (default 7200 s) + UNIQUE constraint `(subscription_id, bout_id, fired_at_hour)` en `alert_log`. | Sesión 2 | Evita avisos duplicados caros/molestos. Redis rápido + BD atómico. |
| D17 | Reintentos de llamada: **3 intentos con backoff exponencial 1 s / 5 s / 30 s**. Si todos fallan → log `error` + marcar `failed`. | Sesión 2 | Backoff tolera fallos transitorios del proveedor SIM sin sobrecargar. |
| D18 | Buffer inter-combates por defecto: **5 min**. | Sesión 2 | Promedio observado en UFC cards (4-7 min). Se calibrará con datos reales en Fase 2. |
| D19 | Zona horaria: **UTC interno** en BD/estimaciones; presentación al usuario en `users.timezone` (default `Europe/Madrid`). | Sesión 2 | Best practice estándar; usuario es español. |
| D20 | Política de fallos ESPN: **backoff exponencial con jitter** (1→60 s cap) + **circuit breaker** (5 fallos/min → 60 s open). Sin fallback offline. | Sesión 2 | Patrón estándar; circuit breaker evita abrasa a ESPN cuando está mal. |
| D21 | Web admin: **Jinja2 + HTMX** monolítico en el mismo proceso FastAPI. | Sesión 2 | Simple, un solo servicio, curva baja. |
| D22 | Postgres local: **docker-compose**. | Sesión 2 | Reproducible, sin instalar en host, fácil para cualquiera que retome el proyecto. |
| D23 | Proveedor SIM (Fase 5): **Twilio** por defecto. | Sesión 2 | API más madura, capa free inicial, doc excelente, TTS estándar. |

---

## Decisiones pendientes

> **Pendientes en futuras sesiones**:

1. **Modelo de datos exacto** (tablas/columnas): se diseña al iniciar Fase 2, cuando `EstimatorEngine` ya sepa qué necesita guardar.
2. **Calibrado del buffer inter-combates** (D18): refinar 5 min con datos reales tras Fase 2 smoke test.
3. **Caché de última tarjeta conocida en Redis TTL 60 s como fallback** si ESPN cae más de ~3 min (opcional, no decidido).
4. **Cobertura deportiva ampliada** (Bellator/PFL, Boxeo, Tenis): fuera del MVP, Fase 4.

---

## Arquitectura

```
                +-----------------------------+
                |        FastAPI app          |
                |  (REST auth + admin web)    |
                +-------------+---------------+
                              |
            +-----------------+-----------------+
            |                                   |
   +--------v---------+              +---------v----------+
   |   Providers       |              |   EstimatorEngine   |
   | - ESPN UFC         |              | - recálculo         |
   | - TheSportsDB     |              |   según combate previo
   | - Scraping Tenis  |              | - regla "X min antes"|
   +--------+---------+              +---------+----------+
            |                                   |
            +-----------------+-----------------+
                              |
                     +--------v--------+
                     | APScheduler poller
                     | (cada N seg/combate)|
                     +--------+--------+
                              |
                     +--------v--------+
                     | Notifier dispatcher
                     | - VoiceNotifier  |
                     |   (mock por ahora)|
                     +-----------------+
```

### Flujo de una alerta
1. **Poller** (APScheduler) consulta cada N segundos el provider del evento suscrito.
2. **Provider** devuelve la card con estado de cada combate (`scheduled`/`in_progress`/`ended`) y tiempos reales.
3. **EstimatorEngine** detecta transiciones de estado del combate inmediatamente anterior al objetivo y recalcula `start_estimado`:
   - Combate `n-1` en `in_progress` → `start_n ≈ now + (duración_media - ya_transcurrido)`.
   - Combate `n-1` en `ended` → `start_n = now + buffer_intercombate`.
4. Si `start_estimado - now ≤ X_min_configurado` y no se ha disparado ya la alerta para esa suscripción → **notifier.call(user, bout_info)**.
5. **alert_log** registra todo en BD (auditable desde admin).

### Entidades clave (Draft — concretar en Fase 0)
- `users` (id, email, phone_normalized, role)
- `sports_subscriptions` (user_id, sport)
- `event_subscriptions` (user_id, event_id, lead_minutes)
- `bout_subscriptions` (user_id, bout_id, previous_bout_id, lead_minutes, status)
- `notification_channels` (user_id, type=phone, config_json)
- `alert_log` (subscription_id, fired_at, payload, notifier_response)

---

## Stack tecnológico

| Capa | Tecnología | Versión objetivo |
|------|-----------|------------------|
| Lenguaje | Python | 3.12+ |
| API/framework | FastAPI (async) | última |
| Scheduler | APScheduler | 3.x |
| Persistencia | SQLAlchemy 2.x async + Alembic | 2.x |
| BD relacional | PostgreSQL | 16 |
| State temporal | Redis | 7 |
| HTTP client | httpx | última |
| Tests | pytest + pytest-asyncio + respx | — |
| Lint/format | ruff + black + mypy | — |
| Contenedor | docker-compose (app, db, redis) | — |
| Web admin | Jinja2 + HTMX (decisión D21) | — |
| Proveedor SIM | Twilio (decisión D23, Fase 5) | — |

Dependencias se materializan en `pyproject.toml` en la **Fase 1 (Scaffold)**.

---

## Fuente de datos (investigación)

### Resumen

| Deporte | Fuente primaria | Auth | ¿Estado en vivo por combate? | Fallback (scraping) |
|---------|----------------|------|-----------------------------|---------------------|
| **MMA — UFC** | **ESPN Core API** `https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc/` | No | **Sí** (state + clock + period por fight) | fuera del MVP (D11) |
| **MMA — Bellator/PFL** | TheSportsDB (a estudiar cuando se amplíe) | API key gratuíta | Limitado | tapology.com |
| **Boxeo** | (fuera del MVP) | — | — | — |
| **Tenis ATP/WTA** | (fuera del MVP) | — | No | flashscore.es / tennistemple.com |

### Hallazgos ESPN verificados en vivo (Sesión 2)
- **Evento de prueba**: UFC 329 *McGregor vs Holloway 2* (11 jul 2026) → devolvió **14 combates** con tarjeta completa.
- Endpoints:
  - `GET /events?seasontype=2` → lista eventos de la temporada.
  - `GET /events/{eventId}` → evento + array `competitions[]` con todos los combates.
  - `GET /events/{eventId}/competitions/{competitionId}/status` → `{clock, period, type:{state:"pre"|"in"|"post", completed}}`.
- **Campos clave por combate** (todos presentes y verificados):
  - `matchNumber` (1–14) → **orden explícito**, 1 = main event ⭐
  - `cardSegment.name` → "main" / "prelims1" / "prelims2"
  - `date` / `endDate` por combate
  - `format.regulation.periods` → 3 o 5 rounds
  - `format.regulation.clock` → 300 seg/round
  - `competitors[].order` (1=red, 2=blue), `winner`, `athlete $ref`

### Notas
- ESPN no requiere auth, pero respeta rate-limit implícito; usar `httpx` con backoff exponencial con jitter (D20).
- ESPN Core API es la fuente que usa el propio ESPN.com; alta fiabilidad.
- TheSportsDB queda reservado para Bellator/PFL (D12), fuera del MVP actual.

### Tareas pendientes de validación (Fase 0)
- [ ] Confirmar campos de atleta (`/athletes/{id}`) para mostrar nombre en alerta.
- [ ] Validar behavior del status endpoint durante combate en vivo (cuando `state:"in"`).

---

## Estructura de carpetas prevista

```
Avisador v2/
├─ README.md                  # este archivo (documento vivo)
├─ AGENTS.md                  # chuleta ejecutable para LLMs
├─ memoria/                   # docs de sesión y arquitectura
│  ├─ handoff.md              # estado actual + próximo paso
│  └─ arquitectura.md         # snapshot del diseño (diagrama, flujo, stack)
├─ pyproject.toml
├─ .env.example
├─ docker-compose.yml
├─ alembic/
│  └─ versions/
├─ src/app/
│  ├─ main.py
│  ├─ config.py
│  ├─ db/
│  │  ├─ session.py
│  │  └─ models/
│  ├─ domain/                 # entidades puras
│  ├─ providers/
│  │  ├─ base.py              # interfaz Provider
│  │  ├─ espn_ufc.py
│  │  ├─ thesportsdb_mma.py
│  │  ├─ thesportsdb_boxing.py
│  │  └─ scrap_tennis.py
│  ├─ engine/
│  │  ├─ estimator.py         # recálculo según combate previo
│  │  ├─ poller.py            # APScheduler jobs
│  │  └─ state.py             # redis state
│  ├─ notifiers/
│  │  ├─ base.py              # interfaz VoiceNotifier
│  │  └─ dummy.py             # log-only (placeholder)
│  ├─ api/
│  │  ├─ auth.py
│  │  ├─ users.py
│  │  ├─ subscriptions.py
│  │  └─ admin.py
│  ├─ web/
│  │  └─ templates/           # admin HTMX (tentativo)
│  └─ tests/
└─ docs/                      # apuntes adicionales (no duplicar README)
```

---

## Fases de implementación

### Fase 0 — Providers ESPN UFC + tests
- [ ] Interfaz `Provider` (`base.py`) con `list_upcoming_events`, `get_event_card`, `get_competition_status`
- [ ] Implementación `espn_ufc.py` con httpx async + backoff exponencial con jitter (D20) + circuit breaker (D20)
- [ ] **Fixtures JSON grabadas** en `tests/fixtures/espn_ufc/`: event_list.json, event_600059148.json, competition_status_pre.json, competition_status_in.json, competition_status_post.json
- [ ] Tests unitarios en `tests/test_espn_ufc.py` con `respx` (mock httpx):
  - [ ] Listar eventos devuelve lista no vacía.
  - [ ] Detalle evento devuelve los 14 combates con `matchNumber` ordenado y `cardSegment`.
  - [ ] Parser de `status.type.state` distingue `pre`/`in`/`post`.
  - [ ] Backoff retry en 429/5xx (con juч-ed delays).
  - [ ] Circuit breaker abre tras N fallos consecutivos.
- [ ] Script runnable `scripts/probe_espn.py` (smoke manual: próximo evento + número de combates).
- [ ] Validación: alta del atleta para mostrar nombre en alerta.

### Fase 1 — Scaffold ✅ (completada en Sesión 2)
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
- [x] **Verificación**: `pip install -e .[dev]` ✅ + `pytest` (2/2 pasan) ✅ + `ruff check src` ✅ + `uvicorn app.main:app` responde `/health` con `{"status":"ok","env":"development"}` ✅. `docker compose up -d` pendiente (requiere reiniciar Windows para activar Docker Desktop).
- [ ] `alembic upgrade head` pendiente (requiere Postgres levantado).

### Fase 2a — EstimatorEngine puro
- [ ] `domain/entities.py` (Bout, Card, EstimatedStart, Subscription)
- [ ] `engine/estimator.py` con lógica pura de recálculo:
  - [ ] transición `pre → in` del combate previo → estimación por duración media.
  - [ ] transición `in → post` del combate previo → `start = now + buffer_intercombate` (D18).
  - [ ] regla "X minutos antes" configurable por suscripción.
- [ ] **Tests aislados** con reloj fake (`freezegun`) y provider fake; sin Redis, sin BD.

### Fase 2b — Poller + idempotencia
- [ ] `engine/state.py` con Redis (registro de alertas ya disparadas): `SET alert:{sid}:{bid}:{status} 1 EX {ttl}` (D16).
- [ ] `engine/poller.py` con APScheduler async + cadencia adaptativa D15 (60/10/5 s).
- [ ] `notifiers/dummy.py` (log-only) para validar sin llamadas reales.
- [ ] `notifiers/base.py` con interfaz `VoiceNotifier`.
- [ ] Modelos BD mínimos: `users`, `bout_subscriptions`, `alert_log` con UNIQUE constraint `(subscription_id, bout_id, fired_at_hour)` (D16).
- [ ] Reintentos 1 s/5 s/30 s con backoff (D17).
- [ ] **Tests end-to-end** simulando transiciones de estado del combate previo.

### Fase 3 — Multiusuario + admin web
- [ ] Esquema BD completo + migraciones Alembic (extiende lo de Fase 2b).
- [ ] Auth JWT (registro / login / refresh).
- [ ] API REST: users, subscriptions, alert_log (CRUD).
- [ ] Panel admin Jinja2 + HTMX (D21).
- [ ] Tests de integración API + BD test.

### Fase 4 — Boxeo/Tenis reales (fuera del MVP)
- [ ] Implementar `scrap_tennis.py` (flashscore/tennistemple) si ampliamos a tenis.
- [ ] Boxeo: integrar si TheSportsDB o ESPN cubren la card ordenada.
- [ ] Bellator/PFL: usar TheSportsDB (D12).
- [ ] Tests con HTML fixtures grabados.

### Fase 5 — VoiceNotifier real
- [ ] Implementar `TwilioNotifier` (D23) con `twilio` SDK.
- [ ] Plantilla TTS del mensaje: "Tu combate X vs Y comenzará en breve, annonce por la tarjeta de UFC XXX".
- [ ] Tests con mocks de la API de Twilio.

---

## Estado actual

**Última actualización**: Sesión 3 (directorio `memoria/` creado)

- [x] Visión y captura de requisitos del usuario (Sesión 1).
- [x] Investigación de fuentes de datos y **verificación en vivo de ESPN Core API** (Sesión 2).
- [x] Decisiones D1–D8 documentadas (Sesión 1).
- [x] Decisiones D9–D23 documentadas (Sesión 2): fuente de datos, polling, idempotencia, reintentos, defaults.
- [x] Entorno: Python 3.12.10 y Docker Desktop instalados vía `winget` (Sesión 2).
- [x] Reordenación de fases: Fase 0 = providers, Fase 1 = scaffold.
- [x] **Fase 1 (Scaffold) completada**: estructura de archivos, `pyproject.toml`, Docker compose, Dockerfile, FastAPI mínimo con `/health` y `/`, `config.py` con pydantic-settings, `db/session.py` async, Alembic con migración `0001` vacía, `AGENTS.md`, `.gitignore`, `.env.example`, `tests/test_health.py`.
- [x] Verificación: `pip install -e .[dev]` OK, `pytest` (2/2 pasan), `ruff check` OK, uvicorn levanta y `/health` responde `{"status":"ok","env":"development"}`.
- [ ] **Próximo paso** → **Fase 0 (Providers ESPN + tests)**.

### Notas de entorno
- Python 3.12.10 instalado en `C:\Users\pacor\AppData\Local\Programs\Python\Python312\` (PATH user).
- venv local en `.venv` ya creado y deps instaladas. Re-activa con `.\.venv\Scripts\Activate.ps1`.
- Docker Desktop instalado; requiere **reiniciar Windows** para que el daemon Docker arranque. Hasta entonces `docker compose up` y `alembic upgrade head` (que necesita Postgres) no funcionarán. La app FastAPI y los tests sí funcionan sin BD/Redis.
- Siguiente sesión: arrancar Fase 0 (providers ESPN + tests) sin necesidad de BD/Redis; Postgres+Redis puede arrancarse más adelante cuando sean necesarios (Fase 2b/3).

---

## Cómo continuar la tarea

Si eres un LLM o persona que retoma el proyecto:

1. **Lee `memoria/handoff.md`** — es el punto de entrada más rápido: estado, último avance, próximo paso.
2. **Lee este README completo** para entender decisiones, fases y contexto.
3. Revisa [Estado actual](#estado-actual) y los checkboxes de cada fase.
4. **Pregunta al usuario** por las [Decisiones pendientes](#decisiones-pendientes) si alguna queda abierta y bloquea tu siguiente paso.
5. Trabaja de sliced: completa un sub-item de la fase activa, ejecuta tests/lint, y actualiza:
   - Marca el checkbox completado.
   - Añade entrada en la [Bitácora](#bitácora-de-sesiones) con fecha, qué se hizo y qué queda.
   - Actualiza `memoria/handoff.md` con el nuevo estado.
6. **No asumas** decisiones ya tomadas (tabla Decisiones); si necesitas cambiar una, añade decisión nueva (`D24`, `D25`...) con justificación, **no edites** la histórica.
7. Mantén el README conciso y accionable; evita bloques de texto largo sin propósito.

---

## Convenciones del proyecto

- **Idioma**: código e identificadores en inglés; comentarios y docs en español.
- **Commits**: conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`) — a confirmar en Fase 0.
- **No subir secrets**: `.env` nunca se commitea; solo `.env.example`.
- **Testing**: todo provider/notifier/engine tiene tests; la web admin se puede cubrir más adelante.
- **Async-first**: todas las I/O (httpx, BD, redis) deben ser async.
- **Type hints**: obligatorios en todo el código nuevo.
- **Lint**: ruff + black. CI debe pasar antes de mesclar.
- **No comentarios** en código salvo que expliquen "por qué" no-trivial.

---

## Bitácora de sesiones

### Sesión 1 — _Inicio del proyecto_
- Recogida de requisitos con el usuario vía preguntas estructuradas.
- Investigación de fuentes de datos gratuitas para MMA/Boxeo/Tenis.
- Definición de stack (Python + FastAPI + APScheduler + Postgres + Redis) — decisiones D1-D8.
- Definición de arquitectura pluggable por deporte (D3).
- Creación de este README como documento vivo (D8).
- **Pendiente para próxima sesión**: confirmar Fase 1 y arrancar trabajo.

### Sesión 3 — _Handoff y directorio memoria_

- Clonado el repo desde `https://github.com/theni55/DespertarME.git` en `C:\Users\javier.romero\Personal\DespertarME`.
- Creado directorio `memoria/` con:
  - `arquitectura.md` — snapshot del diseño (diagrama, flujo, entidades, stack, decisiones).
  - `handoff.md` — estado actual de la sesión, próximo paso, notas de entorno, comandos quick-start.
- Actualizado `AGENTS.md`: nuevas reglas de lectura (handoff → README → arquitectura) y obligación de actualizar `handoff.md` al final de cada sesión.
- Actualizado `README.md`: añadido `memoria/` a estructura de carpetas y `handoff.md` como punto de entrada en "Cómo continuar".
- **Pendiente para próxima sesión**: Fase 0 — Providers ESPN + tests.


- **Verificación en vivo de APIs**: ESPN `site.api.espn.com` devolvía 404; ESPN `sports.core.api.espn.com/v2` funciona con datos reales (UFC 329, 14 combates, statuses). TheSportsDB sin tarjeta útil. ufcstats.com no conecta desde este entorno.
- Nuevas decisiones **D9–D23**:
  - Fuente de datos: ESPN Core API única (D9-D14). TheSportsDB y scraping fuera del MVP (D10-D12).
  - Polling adaptativo 60/10/5 s (D15). Idempotencia Redis+BD UNIQUE (D16). Reintentos 1/5/30 s (D17).
  - Defaults: buffer 5 min (D18), UTC interno + tz usuario (D19), backoff+jitter+circuit breaker ESPN (D20), Jinja2+HTMX (D21), docker-compose (D22), Twilio (D23).
- **Reordenación de fases**: Fase 0 = providers ESPN + tests; Fase 1 = scaffold; Fase 2 dividida en 2a (estimador puro) y 2b (poller + idempotencia).
- **Instalación de entorno via winget**: Python 3.12.10 + Docker Desktop. Docker requiere reiniciar Windows para que arranque el daemon.
- **Fase 1 (Scaffold) completada**: creados `.gitignore`, `.env.example`, `pyproject.toml` (deps runtime + dev + ruff/black/mypy/pytest config), `docker-compose.yml`, `Dockerfile`, `src/app/{__init__.py, main.py, config.py, db/{__init__.py, session.py, models/__init__.py}}`, `alembic.ini` + `alembic/{env.py, script.py.mako, versions/0001_baseline.py}`, `AGENTS.md`, `tests/{__init__.py, conftest.py, test_health.py, fixtures/.gitkeep}`.
- **Verificación funcional**: `pip install -e .[dev]` OK · `pytest` 2/2 pasan · `ruff check src tests` All checks passed · `black` 9 files OK · `uvicorn app.main:app` levanta y `GET /health` responde `{"status":"ok","env":"development"}` y `GET /` responde `{"name":"avisador","version":"0.1.0","docs":"/docs"}` · `alembic heads` muestra `0001 (head)`.
- **Pendiente para próxima sesión**:
  1. Reiniciar Windows para activar Docker Desktop y luego `docker compose up -d` (Postgres+Redis) + `alembic upgrade head` (no bloqueante para Fase 0).
  2. Arrancar **Fase 0 — Providers ESPN + tests**: interfaz `Provider`, `espn_ufc.py` con httpx+backoff+circuit breaker (D20), fixtures JSON grabadas, tests con `respx`, script `scripts/probe_espn.py`.