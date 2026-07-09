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

## Sesión 5 — MVP launch (fotos de peleadores + Twilio + scheduler + Railway)

Objetivos del owner para dejar el MVP lanzado: peleas con cara/nombre de cada
peleador, sesión de usuario + datos desde admin, y llamadas Twilio en el
momento adecuado. Decisiones de alcance tomadas con el owner: Railway como
plataforma (Vercel/CF Pages descartados: serverless no soporta el scheduler
24/7), Postgres + Redis add-ons, scheduler in-process 1 worker, Twilio gated
(aún sin cuenta), teléfono obligatorio E.164.

- **WS1 Peleadores**: `get_athlete()` + `AthleteDetail` (verificado en vivo:
  `displayName` + `headshot.href`); `AthleteRef.athlete_id` (regex sobre
  `$ref`); `AthleteResolver` (D32) con caché Redis TTL 7d + memoria compartida
  + lote de 4 concurrentes, degradación a "TBD"; `event_detail.html` con
  headshots (borde rojo/azul por esquina) y placeholder SVG.
- **WS3 Twilio + scheduler**: `TwilioNotifier` (TwiML inline es-ES ×2,
  `asyncio.to_thread`); `build_notifier()` gated por las 3 env-vars (D30);
  Poller cableado con datos reales (User.phone_normalized, nombres, evento) y
  skip de usuarios sin teléfono/inactivos — **bugfix**: el mapeo usaba el id
  del competitor como id de atleta; `scheduler.py` con `AsyncIOScheduler` en
  lifespan (D31), `SCHEDULER_ENABLED` flag; teléfono obligatorio E.164 en
  registro web y API (`auth/validators.py`, D34).
- **WS2 Admin**: `/admin/users/{id}` (teléfono, suscripciones, historial de
  alertas) + toggle activar/desactivar (con guard anti-auto-desactivación) +
  link desde la lista.
- **WS4 Deploy**: `railway.json` (healthcheck `/health`, migraciones en start);
  Dockerfile prod (sin deps dev, `--workers 1`); normalización de
  `DATABASE_URL` PaaS → asyncpg; guard `JWT_SECRET` en producción;
  `.env.example` actualizado.
- **Entorno**: este clon no tenía venv; creado con `py -3.12` (el `python` del
  PATH es 3.11).
- **Verificación**: `pytest` 72/72 ✅ (22 nuevos: notifiers, athletes, poller
  payload/skip, get_athlete, teléfono API) · ruff ✅ · black ✅ · mypy ✅ ·
  smoke server (health, login user/admin, scheduler arranca con Dummy gated) ·
  smoke E2E en vivo contra ESPN: registro + eventos + detalle con **28
  headshots y nombres reales**.
- **Pendiente**: ejecutar el deploy en Railway (cuenta owner); credenciales
  Twilio; rotar el token GitHub embebido en el remote (aviso de seguridad).

## Sesión 6 — Rediseño visual + landing dinámica (D35, en curso)

- Owner pidió "lavado de cara" vistoso/llamativo + landing dinámica. Se
  investigaron 3 repos de skills para agentes frontend (`nexu-io/open-design`,
  `addyosmani/agent-skills`, `msitarzewski/agency-agents`) y se debatió Jinja2
  vs SPA: **se decide construir sobre Jinja2** (D35) — el motor de plantillas
  no limita el diseño visual; migrar a SPA obligaría a rehacer la auth por
  cookie sin ganar nada en "vistosidad".
- **Fase 0**: instalado el subset frontend de `addyosmani/agent-skills` en
  `.opencode/skills/` (`frontend-ui-engineering`, `performance-optimization`,
  `code-review-and-quality` + checklist de accesibilidad).
- **Fase 1**: `StaticFiles` montado en `main.py`; fuente **Inter Variable**
  auto-hospedada (`static/fonts/inter-var-latin.woff2`, ~48KB, descargada de
  `cdn.jsdelivr.net/fontsource` y verificada por magic bytes `wOF2`).
- **Fase 2**: CSS extraído de `base.html` a `static/css/app.css` con design
  tokens completos (color/spacing/tipografía/motion/sombras) y refresco de
  **las 12 plantillas** (auth con labels visibles, tablas envueltas en
  `.table-wrap` para responsive, utilidades para eliminar CSS inline
  repetido: `.nav-user`, `.inline-form`, `.btn-sm`, `.event-row`, etc.).
  Accesibilidad: skip-link, foco visible, `prefers-reduced-motion`.
- **Fase 3**: `landing.html` nueva (hero, cómo funciona, deportes, CTA,
  footer) + `static/js/reveal.js` (reveal-on-scroll vanilla, progressive
  enhancement). `main.py`: `/` sirve la landing siempre (antes 302 a `/app`,
  ahora pública incluso con sesión activa — decisión explícita del owner).
- **Fase 4 (parcial)**: extraído `partials/_alert_cell.html` de
  `event_detail.html` con atributos `hx-post`/`hx-target` ya escritos, pero
  el backend (`web/user.py`) **todavía no** detecta `HX-Request` para
  devolver el partial — pendiente de completar.
- **Verificación parcial**: `ruff` ✅ `black` ✅ `mypy` ✅. `pytest`: **2
  tests en rojo** (`test_root_redirects_to_app` en `test_health.py` y
  `test_api.py`, esperan 302 y ahora es 200 — cambio esperado, falta
  actualizarlos), 70 verdes. Smoke HTTP manual (`curl`/`Invoke-WebRequest`)
  confirma 200 en `/`, `/app/login`, `/app/register`, CSS y fuente sirven
  bien. **Falta** revisión visual real en navegador y breakpoints.
- **Hallazgo suelto**: fichero `imagen landing.jpeg` sin trackear en la raíz
  del repo — probablemente referencia visual del owner para el hero, sin
  incorporar todavía.
- **Pendiente**: completar Fase 4 (HTMX real en create/delete alert), Fase 5
  (arreglar los 2 tests, smoke visual en navegador, decidir sobre la imagen
  suelta, actualizar `handoff.md` al cerrar).

## Sesión 6 (cont.) — Landing rediseñada a pantalla única (D36)

- El owner pidió cambiar la landing recién creada: **una única pantalla sin
  scroll**, con `imagen landing.jpeg` (póster oficial UFC 329, McGregor vs
  Holloway 2) de fondo, **un solo botón "Avísame"** hacia el registro, y
  dinamismo visual con partículas/movimiento de fondo. Antes de tocar código
  se resolvieron 4 decisiones vía preguntas estructuradas: acceso de usuarios
  existentes (enlace "Entrar" discreto arriba), técnica de partículas
  (**tsparticles vía CDN**, descartando CSS-only por ser muy limitado y
  canvas propio por menor riqueza visual), tratamiento de la imagen (fondo
  full-bleed + overlay, no recuadro central) y optimización (generar
  WebP+JPG con `ffmpeg`, no servir el 1MB original).
- **Imágenes**: `ffmpeg` (ya instalado vía winget) generó
  `static/img/hero.webp` (161KB, calidad 80) y `static/img/hero.jpg` (202KB,
  fallback `<picture>`) a 1600px de ancho desde el JPEG original de 1MB.
  El fichero suelto `imagen landing.jpeg` de la raíz **se eliminó** tras
  copiar su contenido optimizado (cierra el hallazgo pendiente de la sesión
  anterior).
- **`landing.html` reescrita por completo**: `.hero-screen` a `100svh` con
  `<picture>` (webp/jpg) de fondo, capa `.hero-overlay` (degradado oscuro +
  glow rojo radial) para legibilidad, `#tsparticles` para el movimiento,
  nav superior mínima (marca + "Entrar") y contenido central (kicker + h1 +
  lead + botón `.btn-wake` "Avísame" con animación de brillo pulsante vía
  `@keyframes wake-glow`, respetando `prefers-reduced-motion`). Se eliminan
  las secciones de marketing (cómo funciona, deportes, CTA final, footer) —
  ya no encajan en una pantalla única.
- **tsparticles 2.12.0** cargado por CDN (`cdn.jsdelivr.net`, versión
  pinneada) con init inline guardado tras `matchMedia("(prefers-reduced-motion: reduce)")`
  y tras `window.load`; partículas tipo "chispas" (rojo/coral/dorado,
  movimiento ascendente lento, repulsión al hover). Progressive enhancement:
  sin JS o con reduced-motion, la landing es 100% funcional sin partículas.
- **CSS**: se sustituyó todo el bloque de landing de D35 (hero con
  `max-width`, `.section`, `.steps`, `.sport-card`, `.cta-final`,
  `.landing-footer`, animaciones `[data-reveal]`) por los estilos de
  pantalla única. Se añadió salvaguarda `@media (max-height: 560px)` que
  reactiva el scroll vertical en móviles apaisados muy bajos, para que el
  CTA nunca quede cortado por el `overflow: hidden` estricto.
- **Limpieza de dead code**: `reveal.js` y la clase `data-reveal`/`reveal-init`
  ya no los usa nadie (solo la landing anterior) → se eliminó el fichero y su
  `<script>` en `base.html`.
- **Tests**: se aprovechó para cerrar los 2 tests rojos heredados de la
  sesión anterior (`test_root_redirects_to_app` en `test_health.py` y
  `test_api.py`, que esperaban 302). Se reescribieron como
  `test_root_serves_landing` (200 + contiene "Avísame"), sin tocar la
  cobertura ya existente de `/app` sin cookie → redirige a `/app/login`
  (`test_api.py` líneas 196-198, intacta).
- **Verificación completa**: `ruff` ✅ · `black` ✅ · `mypy` ✅ · `pytest`
  **72/72 verdes** (0 rojos, primera vez desde que empezó la Fase 6). Smoke
  HTTP manual sobre el `uvicorn --reload` ya corriendo: `/` 200 con
  "Avísame" y script de tsparticles, `static/img/hero.webp` y `hero.jpg`
  sirven con el tamaño esperado, `/app` sin cookie → 303 a `/app/login`
  (200).
- Nueva decisión **D36** (ver `decisiones.md`).
- **Pendiente**: smoke visual real en navegador (breakpoints 320/768/1024/1440,
  contraste del texto sobre la imagen, foco de teclado en "Entrar"/"Avísame",
  verificar que las partículas no molestan en pantallas pequeñas), completar
  Fase 4 (HTMX real en create/delete alert, sigue sin tocar), y cuando el
  cartel destacado cambie de evento, regenerar `hero.webp`/`hero.jpg` con el
  póster nuevo.
