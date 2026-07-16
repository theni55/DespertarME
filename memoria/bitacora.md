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

## Sesión 7 — Pivot a app móvil + skills grill (D37/D38)

- El owner decidió pivotar: **web apartada, foco en app móvil**.
- **Planificación con preguntas estructuradas** (en modo plan): stack
  React Native + Expo TypeScript, sin cuentas de usuario (device model),
  notificaciones push FCM tipo despertador, web congelada, admin refactorizado
  a devices, solo UFC v1. Decisiones D37 registradas.
- **Skills instaladas**: `grill-me` y `grilling` desde `mattpocock/skills`
  (`skills/productivity/`) vía git sparse-checkout a `.opencode/skills/`.
  Formato frontmatter compatible con OpenCode. Decisión D38.
- **Memorias actualizadas**: `decisiones.md` (D37, D38 + pendientes Fase 7),
  `fases.md` (Fase 6 congelada, Fase 7 detallada), `handoff.md` (nueva sesión,
  estado global, próximos pasos), `bitacora.md` (esta entrada).
- **En curso**: sesión de grilling con el owner para cerrar decisiones
  pendientes de implementación de Fase 7 (estructura de proyecto, auth device,
  payload FCM, tipo de sonido de alarma, persistencia de device_id, navegación).
- **Pendiente tras grilling**: crear skill `ship-polished-ui` (pospuesta de
  Sesión 6), arrancar Fase 7a (backend device model + JSON endpoints + FCM).
- **Verificación en vivo**: rama `web` verificada como auto-contenida — todos
  los endpoints (landing, admin, user, static) responden 200. Se levanta sola
  con checkout + pip install + alembic + uvicorn.
- **Grilling completado**: 17 decisiones de implementación resueltas una a
  una vía `grilling` skill (`mattpocock/skills`). Plan de Fase 7 consolidado:
  estructura proyecto (`mobile/` en raíz), auth device (header `X-Device-Id` +
  `expo-secure-store`), eliminación de User/Twilio/teléfono/auth JWT, payload
  FCM descriptivo, sonido custom embebido, Expo Router Tabs, selector minutos
  fijo (5/10/15/30/60), design tokens reusados de la web, Home con póster +
  botón "Avísame" + "Eventos", admin diferido, Firebase en Fase 7a, desarrollo
  Android con emulador (Android Studio gratuito), spike Expo Go en iPhone para
  validar plomería push, API mínima (8 endpoints) + test-alarm, Device schema
  mínimo viable. PR #5 creado para sync `main` → `dev`.
- **Memorias actualizadas**: `decisiones.md` (D37 ampliado con 17 decisiones +
  pendientes post-MVP), `fases.md` (Fase 7 reescrita con Spike + 7a + 7b + 7c
  + 7d detallado), `handoff.md` (grilling completado, próximo paso: spike Expo
  Go), `bitacora.md` (esta entrada).

## Sesión 8 — Cambio de spike (D39): Expo Go+iPhone → dev build Android físico (solo sonido)

- El owner consiguió un móvil Android físico hoy (ventana de varias horas con
  hardware).
- **D39 registrada**: sustituye la decisión #13 de D37. El spike deja de ser
  Expo Go en iPhone (solo plomería push) y pasa a **dev build Android físico**
  vía EAS Build cloud (sin Android Studio en PC).
- **Alcance recortado a solo sonido + bypass DnD**: tras discutir con el owner
  se acordó reducir el spike a lo mínimo necesario — validar que `TYPE_ALARM`
  suena con el móvil en modo No Molestar. **Sin** full-screen intent, **sin**
  `expo-secure-store`, **sin** FCM, **sin** carátula MVP, **sin** Expo Router
  multi-pantalla. 1 pantalla con 2 botones + 2 ficheros Kotlin (~50-70 líneas).
  Razón: el único riesgo que no se puede probar sin hardware real es el bypass
  DnD; cuanto menos Kotlin a ciegas (sin emulador para debugear), menos
  probabilidad de que la primera APK crashee. El full-screen intent, FCM y el
  resto entran en Fase 7b con Android Studio para iterar rápido.
- Solo se actualiza la #13; el resto de D37 intacto (incluida #11 Firebase en
  7a y #12 build diferido).
- `fases.md` Fase 7-Spike reescrita (reducida); `decisiones.md` D39 actualizada;
  `handoff.md` Próximos pasos y estado global actualizados.
- **Spike code escrito en `mobile/`** (commit `532201d`, push a `origin/dev`):
  - Scaffold: `npx create-expo-app` (Expo SDK 57 + RN 0.86 + TypeScript).
  - `App.tsx`: 1 pantalla negra con 2 botones (Probar/Parar) + estado del
    servicio. Sin Expo Router, sin secure-store.
  - `npx expo prebuild --platform android` → `mobile/android/` generado.
  - Native module Kotlin en `mobile/android/app/src/main/java/com/despertarme/spike/alarm/`:
    - `AlarmModule.kt` — canal `IMPORTANCE_HIGH` + `setBypassDnd(true)`,
      métodos `startAlarm`/`stopAlarm` expuestos a JS, pide
      `ACCESS_NOTIFICATION_POLICY` si no lo tiene.
    - `AlarmService.kt` — foreground service tipo `mediaPlayback`,
      `RingtoneManager.TYPE_ALARM` (fallback `TYPE_RINGTONE`) en loop con
      `AudioAttributes(USAGE_ALARM)` + `PARTIAL_WAKE_LOCK` (10 min cap).
      Notification `CATEGORY_ALARM` + `setSilent(true)` (sonido por Ringtone,
      no por notification). Limpieza en `onDestroy`.
    - `AlarmPackage.kt` + registro en `MainApplication.kt`.
  - `AndroidManifest.xml`: permisos `ACCESS_NOTIFICATION_POLICY`,
    `FOREGROUND_SERVICE_MEDIA_PLAYBACK`, `POST_NOTIFICATIONS`, `WAKE_LOCK`,
    `VIBRATE` + `<service foregroundServiceType="mediaPlayback"/>`.
  - `eas.json` perfil único `development` (APK internal, `assembleRelease`).
  - `mobile/README.md` con chuleta de build, permisos manuales en el móvil,
    y troubleshooting OEM (`adb logcat`).
  - TypeScript compila limpio (`tsc --noEmit`). Kotlin solo se verifica
    con la build en la nube.
  - `.gitignore` de `mobile/` ajustado: `/android` ya no se ignora (commitea
    el Kotlin custom + manifest editado).
- **Pendiente**: login Expo del owner (gratis, expo.dev) → `eas build` (~30-45
  min cloud) → instalar APK en el móvil + permisos manuales (notificaciones ON,
  "Anular el modo No Molestar" ON, volumen de alarma máximo) → probar: móvil
  en DnD → "Probar alarma" → ¿suena `TYPE_ALARM`? → "Parar". Si no suena:
  `adb logcat` (platform-tools ~5MB standalone) para aislar qué eslabón falla
  (canal, foreground service, DnD, OEM).
- **EAS login hecho** (`theni55` owner). `npx eas init --force --non-interactive`
  creó el proyecto `@theni55/despertarme-spike` (ID
  `7e79b9e4-c187-4216-bbfd-ab2200b392d2`) y lo linkeó en `mobile/app.json`
  (`extra.eas.projectId` + `owner`).
- **Build EAS #1 fallida** (build `f3a519f8`, commit `e998c482`):
  - Estado `ERRORED` en fase `INSTALL_DEPENDENCIES` (~1.5 s, antes de tocar
    Gradle/Kotlin).
  - Causa: `npm ci` decía `package.json and package-lock.json are in sync`
    fallaba con `Missing: typescript@5.9.3 from lock file`.
  - **Root cause real**: el agente (yo) había metido `eas-cli` como
    devDependency del proyecto (`npm i --save-dev eas-cli`) tras el prebuild.
    `eas-cli` es CLI global, no dep de proyecto; ensució el árbol de deps y
    desincronizó el lock sin pensarlo.
  - **Fix**: `npm uninstall eas-cli` + `npm install` (regenera lock sincronizado
    con package.json limpio). Para EAS, usar `npx eas-cli` (descarga efímera) o
    `npm i -g eas-cli` (PC del owner), no meterlo en el proyecto.
- **Build EAS #2 `FINISHED` ✅** (build `960ed029`, commit `81ca690`):
  - Cola: ~6382 s (free tier saturado). Compilación Gradle/Kotlin: ~350 s
    (~6 min) — la primera compilación real del Kotlin a ciegas pasó limpia.
  - APK lista en:
    `https://expo.dev/artifacts/eas/XUKdmgABRh-LmTGg5KxpaYjrD8y6CnBcImGM0Ygq-5c.apk`
    (válido hasta 28-jul-2026).
- **Prueba en móvil Android 14 físico → CRASH ❌**:
  - APK instalada, permiso de notificaciones concedido ("Permitir").
  - Al tocar "Probar alarma" la app **se cierra de golpe sin mensaje** —
    crash de proceso nativo (no capturado por el `catch` de JS, lo que
    descarta errores de puente y apunta a crash en el lado Kotlin o en
    `startForeground`).
  - El "Service: stopped" que mostró la UI antes de morir sugiere que el
    `AlarmService` arrancó y se cayó en seguida.
  - **Sin `adb logcat` todavía** — el owner no ha hecho el setup USB
    (platform-tools + depuración USB). Hace falta el stack trace exacto
    para diagnosticar la línea del Kotlin que crashea.
- **`expo doctor` (bare workflow)**: avisó de que ciertos campos de
  `app.json` (`orientation`, `icon`, `android.adaptiveIcon`, `plugins`...)
  no se sincronizan automáticamente en cada build porque `mobile/android/`
  está commiteado (bare workflow, no managed). Esperado y no problemático
  para el spike: cualquier cambio futuro en `app.json` requerirá
  `npx expo prebuild --platform android --clean` manual + re-commitear
  `android/`. Mismo aviso que apareció en el log de EAS #2
  ("Specified value for android.package in app.json is ignored because an
  android directory was detected").
- Nota: el bypass-silent *no* requiere que el usuario tenga `ACCESS_NOTIFICATION_POLICY`
  concedido para "sonar"—el canal `IMPORTANCE_HIGH` + `setBypassDnd(true)` es
  suficiente por sí solo en Android stock. El permiso DnD solo se pide por si
  hace falta cambiar el estado de DnD programáticamente (caso bonus). El
  volumen de alarma del sistema sí tiene que estar alto (no se puede subir por
  código en Android 14).

## Sesión 9 — Análisis plan de migración + codebase review + D40/D41 (solo memorias, cero código)

- El owner pidió revisar el plan de migración web→móvil (Fase 7) contra la
  codebase, evaluando solidez, mejoras, riesgos y acierto de las decisiones.
  Además planteó la idea de crear alarmas locales en el dispositivo en vez de
  depender exclusivamente de FCM como timbre ("¿no sería más fácil que la app
  creara una alarma en el móvil del usuario?").
- **Decisión estratégica D40 — Arquitectura de alarma híbrida**: la idea del
  owner es correcta en su variante técnica. La app programa alarmas locales
  exactas (`AlarmManager.setAlarmClock` en Android / **AlarmKit** en iOS 26+, 
  nuevo framework de Apple presentado en WWDC25 sesión 230 que garantiza bypass
  de silencio y focus sin Critical Alert Entitlement — verificado contra la doc
  oficial). FCM data-only pasa de "ring now" a "reprogramador" (mensajes
  `update` con `estimated_start_at`, `started`, `cancelled`). Verify-then-ring:
  la alarma local consulta al backend antes de sonar (self-healing). Descartada
  la variante `ACTION_SET_ALARM` (alarma en el Reloj del sistema): no
  actualizable/cancelable fiablemente, sin contexto del combate, varía por OEM.
- **Decisión táctica D41 — Validación emulador-primero**: Android Studio +
  emulador API 34 se adelanta de Fase 7b al spike actual. El emulador valida
  Android estándar (crash E1, sonido `USAGE_ALARM`, DnD, Doze forzado);
  iteración en ~2-5 min local vs ~2 h EAS cloud con logcat integrado sin
  setup USB. El móvil físico queda como confirmación final de quirks OEM
  (Xiaomi/Samsung/Huawei), en dispositivos concretos cuando haya acceso.
- **Codebase review del backend (`src/app/` + `tests/`)**: revisión exhaustiva
  con file:line concretas. Hallazgos clave:
  - **E1 — Crash del spike**: falta `FOREGROUND_SERVICE` en el manifest
    (SecurityException en `startForeground` desde API 28, fuera del try/catch
    del bridge → la app muere sin mensaje JS). 3 defensivos adicionales:
    null-check en `getRingtone()` (`AlarmService.kt:45` puede devolver null),
    quitar `promptPolicyAccess()` del flujo `startAlarm` (lanza Settings +
    innecesario, bitacora:410), guard API 28 en `isLooping`.
  - **E2 — Estimación `post` se desliza al infinito** (`estimator.py:111-118`):
    `start = now + buffer` recalcula en cada poll → delta constante 300 s →
    `lead < 5` nunca dispara. Con D40 la alarma local se reprogramaría al
    infinito. Fix: anclar a primera observación de la transición.
  - **E3 — Poller nunca mira el combate objetivo** (`poller.py:104-122`):
    solo consulta el previo. Puede disparar "empieza en 5 min" horas después
    del combate. Falta guard + tipos de mensaje `started`/`cancelled`.
  - **E4 — `previous_bout_id` congelado por el cliente** (`subscriptions.py:43`)
    vs cartelera viva que usa el estimador: reordenaciones UFC → estimaciones
    incoherentes. Derivarlo server-side y quitarlo del contrato del cliente.
  - **E5 — CB se abre con 404s** (`espn_ufc.py:150-156`): al existir
    `GET /api/events/{id}` público, DoS trivial (5 ids inválidos = poller
    muerto 60 s). Contar solo fallos retryables.
  - **E6 — `fired_at_hour = now.hour`** (`poller.py:252`): colisiona entre
    días distintos; no impide duplicado si un retry cruza cambio de hora. Usar
    `epoch//3600`. Falta UNIQUE `(device_id, bout_id)` — con la app, un tap
    de re-suscribirse generará push duplicados.
  - **E7 — Retries de voz** (36 s sleep por sub fallida, `poller.py:216-218`)
    bloquean el ciclo del poll entero; sin sentido para FCM (idempotente,
    barato). Recortar.
  - **E8 — Sin caché de card por ciclo** (`poller.py:152-166`): N subs =
    N fetches idénticos a ESPN por minuto. Agrupar por `event_id`.
  - **5 trampas de migración para Fase 7a**: (1) `sport_subscriptions`/
    `event_subscriptions` también tienen FK a users (`subscriptions.py:21-39`),
    el plan no las menciona; (2) ENUM `user_role` de PG no se borra solo con
    `drop_table`, requiere `sa.Enum.drop()` explícito; (3) FKs sin naming
    convention en `Base` + migración base autogenerada contra SQLite →
    escribir la de 7a a mano contra PG; (4) `new_uuid` en
    `auth/dependencies.py:57` — lo importa `subscriptions.py:13`, si se borra
    `auth/` en bloque ese router deja de importar; (5) `config.py:74` referencia
    `jwt_secret` en el `model_validator` de producción — si se borra el campo
    sin borrar el validator, la app no arranca.
  - **Fase 7b error de tipo de service**: listaba `FOREGROUND_SERVICE_DATA_SYNC`
    — tipo fuertemente restringido en Android 14+. El spike usa `mediaPlayback`,
    que es lo correcto.
  - **Fase 7d obsoleta**: la premisa "Critical Alert Entitlement" queda
    invalidada por AlarmKit (iOS 26, sin entitlement, schedule de fecha fija,
    ciclo de vida cancelar/reprogramar por id, mismo patrón que Android).
  - Separación provider/dominio/engine excelente — 31 tests sobreviven intactos
    a Fase 7a. Tests actuales de poller/api/notifiers se reescriben
    mecánicamente. Bugs E2/E3/E4 sin cobertura de tests.
  - **Aciertos del plan confirmados**: spike-first (validar lo existencial
    antes que lo bonito), recorte a solo sonido (D39), modelo Device sin
    cuentas (simplifica onboarding), eliminar User/Twilio en vez de convivir
    (split limpio), Android primero + iOS diferido.
- **Memorias actualizadas**: `decisiones.md` (D40 + D41 + limpieza de
  pendientes obsoletas), `fases.md` (Spike rehecho con checklist ejecutable,
  7a ampliada con 13 fixes y 5 trampas, 7b con AlarmScheduler D40 y corrección
  de tipo de service, 7d reescrita con AlarmKit), `handoff.md` (Sesión 9 como
  punto de entrada), `bitacora.md` (esta entrada).
- **Sin cambios de código** — `mobile/` y `src/app/` intactos. La sesión fue
  exclusivamente de análisis y actualización del plan documentado.
- **Pendiente**: el continuador arranca con el Paso 1 del handoff (instalar
  Android Studio + emulador → logcat → fix E1 + defensivos → build EAS #3 →
  validación en móvil físico).

## Sesión 10 — Fix E1 + setup Android SDK local + Hyper-V + build EAS #3 (2026-07-15)

- El continuador ejecutó el Paso 1 del handoff de Sesión 9.
- **Fix E1 aplicado** en 4 archivos (commit `e896b88`, push a `dev`):
  - `AndroidManifest.xml` + `app.json`: añadido `FOREGROUND_SERVICE` (el permiso
    genérico que faltaba, causante del `SecurityException` en `startForeground`).
  - `AlarmModule.kt`: eliminada llamada a `promptPolicyAccess()` del flujo
    `startAlarm` (innecesaria — el canal con `setBypassDnd` basta, y además
    mandaba la app a Settings de DnD justo antes del `startForegroundService`).
  - `AlarmService.kt`: null-check en `getRingtone()` (devuelve null → NPE) +
    guard `if (Build.VERSION.SDK_INT >= 28) { isLooping = true }` (API 28+).
  - TypeScript: `tsc --noEmit` compila limpio.
- **Android SDK instalado (portable, sin winget ni admin):**
  - JDK 17 (Temurin portable zip) en `%LOCALAPPDATA%\jdk-17\jdk-17.0.19+10`.
  - Android CLI tools (cmdline-tools) → layout `latest/` tras mover desde el
    doble anidamiento `cmdline-tools/cmdline-tools/`.
  - sdkmanager instaló: `platform-tools`, `platforms;android-34`,
    `system-images;android-34;google_apis;x86_64`, `emulator`,
    `build-tools;34.0.0`.
  - AVD `pixel_6_api34` creado (Google APIs x86_64).
  - `emulator -accel-check` → **sin aceleración**, Hyper-V apagado. CPU tiene
    extensiones de virtualización pero no están activadas.
- **Hyper-V**: se disparó elevación UAC vía
  `Start-Process powershell -Verb RunAs` con
  `Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All`.
  Pendiente de que el owner apruebe el diálogo UAC y reinicie.
- **Build EAS #3 lanzada** como red de seguridad (build ID `f486f8c5`, cola
  free tier ~1-2h). Commit con los fixes ya incluido.
  URL: https://expo.dev/accounts/theni55/projects/despertarme-spike/builds/f486f8c5-d956-4ce9-ab79-2ed12a39a236
- **Explicación de los 3 caminos de testing al owner**: Camino A (emulador
  local, ~5 min/build, necesita Hyper-V), Camino B (móvil físico + build local
  Gradle sin EAS, necesita USB debugging), Camino C (EAS cloud build, ~2h cola).
  Owner eligió Camino A (emulador).
- **Memorias actualizadas**: `handoff.md` (Sesión 10), `bitacora.md` (esta
  entrada). Commit + push próximos.
- **Pendiente para próxima sesión**: verificar estado EAS #3 + Hyper-V
  (aprobación UAC + reinicio) → si Hyper-V OK: fijar env vars, arrancar
  emulador, compilar local, validar DnD. Si no: Camino B (USB) o esperar EAS.
## Sesión 11 — Spike validado en emulador + móvil físico: fix E1 + bypass DnD funcionando (2026-07-15)

- El owner activó VT-x en la BIOS (ASUS ROG STRIX Z370-F → Advanced → CPU Configuration → Intel Virtualization Technology → Enabled). WHPX quedó operativo (`emulator -accel-check` = "WHPX is installed and usable"). El diálogo UAC de Hyper-V de la Sesión 10 había sido aprobado pero sin VT-x en firmware no servía.
- **Variables de entorno permanentes** fijadas en perfil User: `JAVA_HOME`, `ANDROID_HOME`, `PATH` (emulator + platform-tools + cmdline-tools).
- **Emulador arrancado** (`pixel_6_api34`, WHPX, GPU RTX 2080): boot ~75 s primer intento (cold), ~32 s segundo (snapshot falló en cargar pero cold boot rápido). Snapshot `default_boot` guardado.
- **Build local exitoso** (`gradlew assembleDebug`, 2m 29s): APK debug ~129 MB en `mobile/android/app/build/outputs/apk/debug/app-debug.apk`. Primera compilación Kotlin del spike en local confirmada limpia (solo warnings de deprecación, sin errores). Gradle descargó Gradle 9.3.1 + NDK 27.1.12297006 + CMake 3.22.1 + SDK Build-Tools 36/35 + SDK Platform 36 durante la build.
- **APK instalado** en emulador vía `adb install -r` → "Success". Permiso `POST_NOTIFICATIONS` concedido vía `adb pm grant`.
- **Hallazgo: `gradlew assembleDebug` directo NO empaqueta el JS bundle** dentro del APK. La app abre con Red Box "Unable to load script. Make sure you're running Metro...". Fix: arrancar Metro (`npx expo start`) + `adb reverse tcp:8081 tcp:8081` → la app descarga el JS en vivo del Metro en el host. Para builds standalone (sin Metro), empaquetar con `react-native bundle` (requiere `@react-native-community/cli`).
- **Fix E1 VALIDADO** ✅: "Probar alarma" → app NO crashea, `AlarmService` foreground activo (`isForeground=true`, `category=alarm`, `mediaPlayback`), logcat limpio sin `AndroidRuntime`. El crash de la Sesión 8 estaba causado por falta del permiso `FOREGROUND_SERVICE` → `SecurityException` en `startForeground` (API 28+) → muerte del proceso fuera del try/catch del bridge JS-Native. Hipótesis de la Sesión 9 confirmada al 100%.
- **Bypass DnD VALIDADO** ✅: con DnD "Alarms only" (`zen_mode=1`, `cmd notification set_dnd priority`) + volumen `STREAM_ALARM` al máximo, el ringtone `TYPE_ALARM` con `USAGE_ALARM` suena (logcat: `AudioTrack: stop(16): called with 91283 frames delivered`, MediaPlayer `state:started`). **No** suena con DnD "Total silence" (`zen_mode=2`) — AOSP mutes `STREAM_ALARM` en ese modo. Hallazgo técnico: `setBypassDnd(true)` del canal sale como `mBypassDnd=false` en dumpsys del emulador but el ringtone suena igual (el bypass del canal afecta a la notificación visual, no al stream de audio).
- **Parada limpia VALIDADA** ✅: "Parar" → UI "Service: stopped", `dumpsys activity services` sin ServiceRecord, player released, notificación retirada, logcat limpio.
- **Build EAS lanzada** (build ID `fa4366ee`, con fixes E1 incluidos, commit `0d7dff9`). URL: https://expo.dev/accounts/theni55/projects/despertarme-spike/builds/fa4366ee-ed46-4bfa-9adb-6b8158b88232
- **Confirmación en móvil Android 14 físico del owner** ✅: build `fa4366ee` instalada, fix E1 sin crash, bypass DnD funcionando (mismo comportamiento que el emulador AOSP). **Spike 100% cerrado**: emulador ✅ + físico ✅.
- **Hallazgos técnicos para el continuador**:
  1. `gradlew assembleDebug` directo NO empaqueta el JS bundle — Metro + `adb reverse` necesario.
  2. DnD "Total silence" (`set_dnd on` → `zen_mode=2`) mutes `STREAM_ALARM` en AOSP puro. Usar `set_dnd priority` (`zen_mode=1`, "Alarms only") para validar bypass.
  3. `cmd notification set dnd on` no funciona (comando correcto: `cmd notification set_dnd on`).
  4. `ACCESS_NOTIFICATION_POLICY` no es concedible vía `adb pm grant` (no es runtime permission). El bypass DnD del canal `IMPORTANCE_HIGH` + `setBypassDnd(true)` + `USAGE_ALARM` funciona sin necesitarlo.
  5. `media volume --stream 4 --set 7` no existe en AOSP. Subir volumen con `input keyevent 24` (VOLUME_UP) repetido.
- **Memorias actualizadas**: `handoff.md` (Sesión 11), `bitacora.md` (esta entrada), `fases.md` (Spike completado ✅). Commit + push a `dev` pendientes.
- **Pendiente para próxima sesión**: Fase 7a (backend device model + FCM).
## Sesión 12 — Fase 7a backend Device/FCM: código listo (2026-07-16)

- Plan cerrado con el owner tras confirmar la validación del spike en móvil físico (fix E1 sin crash + bypass DnD funcionando en Android 14 del owner) y cerrar la Sesión 11 en memorias. 3 bloques: (1) limpieza bitácora Sesión 11 (escapes Unicode + BEL chars), (2) cierre spike en memorias + decisión D42 (Home póster McGregor estático MVP + mejora post-MVP póster dinámico), (3) Fase 7a (backend Device/FCM) ejecutada en 8 tandas.

- **Bloque 1 — Bitácora Sesión 11 limpiada**: la sección tenía escapes Unicode literales (`Sesiu00f3n` como texto real, no como carácter) y caracteres de control (`\x07` BEL) que rompían legibilidad. Reescrito con texto limpio UTF-8.

- **Bloque 2 — Spike 100% cerrado en memoria**:
  - `memoria/handoff.md` actualizado: sesión "Spike validado en emulador + móvil físico", Paso 1 marcado como completado, estado global Fase 7 actualizado.
  - `memoria/bitacora.md` Sesión 11: añadido bullet de confirmación en móvil físico.
  - `memoria/fases.md` líneas 198-199: marcados `[x]` Build EAS → móvil + smoke OEM.
  - `memoria/decisiones.md` añadida **D42**: Home de la app con imagen estática de McGregor como fallback MVP y póster dinámico del próximo evento como mejora post-MVP. La mejora pendiente queda registrada en el ítem 6 de "Decisiones pendientes post-MVP".

- **Bloque 3 — Fase 7a backend Device/FCM** (pivot User/Twilio → Device/FCM ejecutado end-to-end):

  - **Tanda 0 (prep):** `Base.metadata.naming_convention` añadida (FK con nombres predecibles); `app/common/ids.py` creado con `new_uuid()` mudado de `auth/dependencies.py:57`; imports migrados en `subscriptions.py:14` y `auth.py:12` (este último se borra en Tanda 2).
  - **Tanda 1 (deps + config):** `pyproject.toml` quita `passlib[bcrypt]`, `bcrypt<5.0`, `pyjwt`, `twilio`, baja `pydantic[email]`→`pydantic`, añade `firebase-admin>=6.5` (instalada v7.5.0 transitive incluido grpcio, google-auth, protobuf). `config.py` borra `jwt_*` (3), `twilio_*` (3) y `_check_production_secrets` (referenciaba jwt_secret) juntos; añade `fcm_credentials_path`/`fcm_credentials_json`. `pip install -e .[dev]` reimporta limpio.
  - **Tanda 2 (borrado):** eliminados `src/app/auth/` (3 ficheros), `notifiers/twilio.py`, `api/routes/auth.py` + `users.py`, `db/models/users.py`, `scripts/seed_admin.py`, `src/app/web/__pycache__/` (3 .pyc huérfanos), `SportSubscription` + `EventSubscription` del modelo (tablas muertas, ningún router las usaba — owner confirmó borrarlas). `main.py` + `api/__init__.py` reescritos sin auth/users.
  - **Tanda 3 (migración Alembic a mano):** `alembic/versions/f7a0001_devices_fase_7a_*.py` (`down_revision=a3657c6166f0`). **Drop-and-recreate** (destructivo: el pivot User→Device no tiene datos migrables). Crea `devices` (id UUID PK, fcm_token, platform, timezone, locale, is_active, last_seen_at, created_at, updated_at), recrea `bout_subscriptions` (device_id FK→devices CASCADE, UNIQUE (device_id,bout_id) E6, sin previous_bout_id/previous_match_number E4) y `alert_log` (device_id FK, `fired_at_epoch_hour` E6, UNIQUE `(subscription_id,bout_id,fired_at_epoch_hour)`). En PG: dropea ENUMs `user_role`/`subscription_status`/`alert_status` explícito (`sa.Enum().drop(checkfirst=True)`). Aplicada en SQLite dev: `alembic upgrade head` verde, `PRAGMA table_info` confirma `device_id` + `fired_at_epoch_hour` ausentes `previous_bout_id`/`user_id`, UNIQUEs presentes.
  - **Tanda 4 (modelos + schemas):** `db/models/devices.py` (Device), `BoutSubscription`/`AlertLog` mutados, `schemas.py` reescrito: `DeviceCreate`/`DeviceOut` (device_id UUID v4 con `min_length=32,max_length=36` + `fcm_token` String min 10), `BoutSubscriptionCreate` **sin** `previous_bout_id` (E4) + `lead_minutes>=5` (E2 sin arreglar de producción), `BoutSubscriptionOut`/`AlertLogOut` con `device_id` (no `user_id`), `EventSummaryOut` con `image_url: None` (D42), `EventCardOut` con `previous_bout_id` calculado server-side.
  - **Tanda 5 (security + API):** `app/security/device.py` con `get_current_device` vía header `X-Device-Id` (estricto — 401 si no registrado, 403 si inactivo; NO autocrea). `api/routes/devices.py`: `POST /api/devices` (upsert token), `DELETE /api/devices/me` (soft delete is_active=False), `POST /api/devices/me/test-alarm` (envía push `fire`). `api/routes/events.py`: `GET /api/events` (caché Redis 5 min best-effort + `include_past_hours` opcional), `GET /api/events/{id}` con `previous_bout_id` server-side derivado de matchNumber+1 (E4). `main.py` re-wired: 4 routers + `close_events_resources` en lifespan.
  - **Tanda 6 (notifiers FCM):** `base.py` mutado — `PushNotifier`/`PushResult`/`AlertPayload` data-only con `message_type` `update`/`started`/`cancelled`/`fire` + `fighters`/`estimated_start_at`/`minutes_until_start`/`weight_class` opcional; `to_data()` omite None. `dummy.py` sin phone. `fcm.py` nuevo: `firebase_admin.messaging.Message(data=..., token=..., android=AndroidConfig(priority="high"))` via `asyncio.to_thread`. `__init__.py` `build_notifier()` gating + `get_notifier()` singleton compartido por scheduler y endpoint test-alarm.
  - **Tanda 7 (engine bugfixes E2–E8):**
    - `estimator.estimate` añade `observed_at: datetime | None` param; branch `post` `start_at = (observed_at or now) + buffer` (E2).
    - `state.py` añade `remember_transition`/`get_transition` (Redis key `transition:{event_id}:{bout_id}` TTL 24 h, NX: primera observación gana) + `get_last_estimate`/`set_last_estimate` (Redis key `estimate:{sub_id}:{bout_id}` idempotencia TTL). Helper `_as_str` para bytes|str de fakeredis.
    - `poller.py` reescrito completo: carga `Device` (no `User`), skip si `is_active==False` o `fcm_token is None`. **E3**: comprueba estado del target → if `in` push `started` (idempotente via `try_mark_fired("started")`), if `post` push `cancelled` + `sub.status="fired"`. **E4**: `prev = card.previous_bout(target)` en runtime (no `sub.previous_bout_id`). **E2**: llama `remember_transition(event_id, prev.id, now)` cuando prev es `post`; pasa `observed_at` al estimador. **E6**: `fired_at_epoch_hour = int(now.timestamp())//3600`, idempotencia marcada **tras** éxito (no antes). **E7**: `RETRY_DELAYS = (2.0,)` (1 retry corto, antes 1/5/30=36s). **E8**: `poll_once` agrupa subs por `event_id` y cachea `Card` por ciclo (1 fetch ESPN/evento vs N). **D40 push on-change**: solo empuja `update` si estimación se movió >`MIN_DELTA_SECONDS=60` (Redis last_estimate). Captura de `sub_id`/`bout_id`/`device_id`/`device_token` al inicio para evitar MissingGreenlet tras rollback del IntegrityError en `_log_alert` (rollback expira instancias → lazy-load async → MissingGreenlet).
    - `espn_ufc.py` **E5**: `_request` solo llama `_on_failure()` si `_is_retryable(exc)` (404 + 4xx no abren CB) — fix al bug que permitía DoS trivial desde `GET /api/events/{id}`. `list_upcoming_events` añade `min_date: datetime | None` (default ahora UTC, filtra pasados) + `asyncio.gather` limitado a 4 concurrentes (N+1 secuencial → paralelo controlado). Helper `_parse_event_date` (`Z`→`+00:00`).
    - `scheduler.py` `misfire_grace_time=120` (no descartar ticks), `build_notifier()`→`get_notifier()` (singleton).
  - **Tanda 8 (tests + lint + types):**
    - `tests/conftest.py`: añade `SCHEDULER_ENABLED=false` + `FCM_CREDENTIALS_*=vacío` vía `os.environ.setdefault` en top antes de importar app. `FakeNotifier` capturador (con `fail_count` para simular fallos). `FakeProvider` refactorizado: `set_target_state` y `set_prev_state` independientes (E3). `make_device` helper.
    - `tests/test_api.py` reescrito (15 tests): registro/upsert/invalid device_id, subscriptions con X-Device-Id (auth-required, 401 si no registrado, 403 si inactivo), `lead_minutes<5` rechazado, UNIQUE (device_id,bout_id) 409, deactivate me, list alerts, test-alarm success con DummyNotifier fallback, health OK.
    - `tests/test_poller.py` reescrito (15 tests): no-push sin movimiento, push `update` con prev `post`, E2 anclaje primera observación, E3 target `in`→`started`, E3 target `post`→`cancelled`+marks fired, E3 idempotencia started, E4 derive previo from card (no persistido), E7 retries 2 attempts max, E6 epoch_hour en log, skip fcm_token=None, skip inactive device, payload con device_id+fighters+event_name, `AlertState` idempotencia básica, `remember_transition` anclaje, `MIN_DELTA_SECONDS=60` contract.
    - `tests/test_notifiers.py` reescrito (8 tests): `to_data` incluye/omite None, `DummyNotifier` success/forced failure, `FcmNotifier` con `firebase_admin` mockeado via `patch.dict('sys.modules')` (mock message_id success, exception → failure), `build_notifier` Dummy sin credenciales, Dummy fallback si init FCM falla.
    - `tests/test_espn_ufc.py`: añadido `test_e5_circuit_breaker_does_not_open_on_4xx` (5 peticiones 404 no abren CB); `test_list_upcoming_events_returns_non_empty_list` ajustado con `min_date=datetime(2026,1,1)` (UFC 329 ya pasó hoy 2026-07-16).
    - **Nuevo `tests/test_events_route.py`** (3 tests): lista devuelve `image_url=None` (D42), detalle deriva `previous_bout_id` server-side (E4), 503 si provider cae.
    - **Total: 78 tests verdes** (54 preexistentes reescritos + 24 nuevos). `ruff check src tests` ✅ · `black --check src tests scripts` ✅ · `mypy src/app` ✅ (37 source files clean). `alembic upgrade head` ✅ en SQLite dev. Smoke `TestClient`: server levanta con `/health` + `/openapi.json` con 9 paths (`/api/devices`, `/api/devices/me`, `/api/devices/me/test-alarm`, `/api/events`, `/api/events/{id}`, `/api/subscriptions`, `/api/subscriptions/{sub_id}`, `/api/alerts`, `/health`).

- **Pendientes externos (no bloquea Fase 7b)**: Firebase project + service account key JSON (Python) → `FCM_CREDENTIALS_JSON` o path a fichero + `google-services.json` para la app Android (manual del owner). Deploy Railway (cuenta del owner).

- **Memorias actualizadas**: `handoff.md` (esta entrada), `bitacora.md` (esta entrada), `fases.md` (Fase 7a marcada completada con resumen ejecutivo inline), `decisiones.md` (D42 + ítem 6 en pendientes). Commit + push a `dev` pendientes.

- **Pendiente para próxima sesión**: Fase 7b — app Android v1 con `AlarmScheduler` (`setAlarmClock` + verify-then-ring D40), refactor `AlarmService` (sonido custom + `AlarmActivity` full-screen), cliente FCM `@reactnative-firebase/messaging`, Expo Router Tabs (Home con `hero.webp` estático D42 / Eventos / Mis Alertas / Ajustes), `expo-secure-store` para `device_id`.
