# Decisiones tomadas

> Registro histórico de decisiones de diseño (D1–D23) y decisiones pendientes. No editar las históricas; añadir nuevas con justificación.

## Regla

**No modifiques** una decisión ya tomada. Si necesitas cambiar una, añade una
nueva (`D24`, `D25`...) con su justificación y referencia a la que sustituye.

## Histórico

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
| D20 | Política de fallos ESPN: **backoff exponencial con jitter** (1→60 s cap) + **circuit breaker** (5 fallos/min → 60 s open). Sin fallback offline. | Sesión 2 | Patrón estándar; circuit breaker evita abrasar a ESPN cuando está mal. |
| D21 | Web admin: **Jinja2 + HTMX** monolítico en el mismo proceso FastAPI. | Sesión 2 | Simple, un solo servicio, curva baja. |
| D22 | Postgres local: **docker-compose**. | Sesión 2 | Reproducible, sin instalar en host, fácil para cualquiera que retome el proyecto. |
| D23 | Proveedor SIM (Fase 5): **Twilio** por defecto. | Sesión 2 | API más madura, capa free inicial, doc excelente, TTS estándar. |
| D24 | Resiliencia ESPN implementada con **`tenacity`** (backoff exponencial con jitter, cap 60 s) + **circuit breaker manual** (N fallos consecutivos → open). | Sesión 4 | Cumple D20 sin reinventar backoff; tenacity es estándar y async. El CB es ~20 líneas (counter + `open_until` con `clock` inyectable para tests). |
| D25 | Entidades de dominio (`domain/entities.py`) como **dataclasses frozen** separadas de los DTOs de parsing (`providers/models.py`). | Sesión 4 | Las entidades de negocio (Bout, Card, EstimatedStart) son inmutables y sin I/O; los DTOs de ESPN son pydantic con alias. Mapeo explícito en el Poller. |
| D26 | BD de desarrollo con **SQLite + aiosqlite** (no Postgres) mientras Docker Desktop no arranca. | Sesión 4 | Permite avanzar Fase 2b y 3 sin Docker. `DATABASE_URL=sqlite+aiosqlite:///./avisador.db` en `.env`. Para producción basta cambiar la URL a `asyncpg`. Dep dev `aiosqlite` añadida. |
| D27 | Redis de tests con **`fakeredis`** en vez de Redis real. | Sesión 4 | Tests sin Docker. Dep dev `fakeredis` añadida. `AlertState` acepta un `redis.Redis` inyectado, compatible con fakeredis. |
| D28 | Auth con **passlib[bcrypt] + PyJWT** (no OAuth2 completo). | Sesión 4 | MVP suficiente: registro/login con JWT, `get_current_user`/`require_admin` como dependencias FastAPI. bcrypt pinned `<5.0` por incompatibilidad con passlib 1.7.4. |
| D29 | Poller sin APScheduler todavía: `Poller.poll_once()` es invocable manualmente. | Sesión 4 | La cadencia adaptativa (D15) ya está en `EstimatorEngine.poll_interval()`. Falta el scheduler real (APScheduler) que llame a `poll_once` periódicamente; se añade al integrar el proceso completo. Tests E2E validan el flujo sin scheduler. |

## Decisiones pendientes

1. **Modelo de datos exacto** (tablas/columnas): se diseña al iniciar Fase 2,
   cuando `EstimatorEngine` ya sepa qué necesita guardar.
2. **Calibrado del buffer inter-combates** (D18): refinar 5 min con datos reales
   tras Fase 2 smoke test.
3. **Caché de última tarjeta conocida en Redis TTL 60 s como fallback** si ESPN
   cae más de ~3 min (opcional, no decidido).
4. **Cobertura deportiva ampliada** (Bellator/PFL, Boxeo, Tenis): fuera del MVP, Fase 4.
