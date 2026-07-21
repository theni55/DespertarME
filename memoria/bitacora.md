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

## Sesión 13 — Code review Fase 7a + 4 fixes bloqueantes (2026-07-16)

- **Contexto**: el compañero (theni55) pusheó a `dev` la Sesión 12 completa (5 commits, `1018cbc..6470b24`): fix E1 del spike + docs Sesiones 10-11 + el commit grande `6470b24` con la Fase 7a (~2.400 líneas). El owner pidió traer los cambios, explicarlos y hacer review formal.

- **Review multi-eje** (skill `code-review-and-quality`) del commit `6470b24`. Veredicto: **request changes** — diseño sólido (idempotencia Redis+UNIQUE en profundidad, E2–E8 bien razonados y testeados, consciencia del MissingGreenlet async) pero 1 Critical + 2 Required + 1 higiene. Verificación del estado recibido: 78 tests verdes, ruff/black/mypy limpios — los tests no podían detectar el bug crítico porque mockean `firebase_admin.messaging` entero.

- **Fixes aplicados (cada uno con test de regresión):**
  1. **[Critical] FCM app nombrada vs default** (`notifiers/fcm.py`): `initialize_app(cred, name="despertarme-fcm")` crea app *nombrada* pero `messaging.send(message, False)` sin `app=` resuelve contra la *default* (inexistente) → `ValueError: The default Firebase app does not exist` en el 100% de envíos reales. Habría explotado en el primer smoke de Fase 7c. Fix: `send(message, False, self._app)` + `get_app(name="despertarme-fcm")` en init para reutilizar app existente al re-instanciar. Assert de regresión: `args[2] is notifier._app` en test de éxito.
  2. **[Required] Caché de events cruzada** (`api/routes/events.py`): clave fija `events:upcoming:ufc` sin `include_past_hours` → el primer request poblaba la caché con su cutoff y durante 5 min todas las variantes recibían esa lista. Fix: flag `cacheable = include_past_hours == 0` — solo la query default (la de la app) lee/escribe. Test nuevo: `test_list_events_cache_only_applies_to_default_query` (fakeredis inyectado en singletons del router, pre-poblado con lista distinta, verifica bypass para query no-default y hit para default).
  3. **[Required] Normalización asimétrica del device_id**: `DeviceCreate._validate_device_id` hace `.strip().lower()` pero `get_current_device` solo `.strip()` → cliente con UUID en mayúsculas se registraba OK (persistido lowercase) y recibía 401 en toda llamada autenticada. Fix: `.strip().lower()` también en la auth. Test nuevo: `test_device_header_is_case_insensitive`.
  4. **[Higiene] `inst_user_settings.tmp`**: temporal del instalador de Android Studio (UTF-16, con rutas locales `C:\Users\pacor\...` del compañero) commiteado por accidente en `f2ad55e` ("emulador"). `git rm` + `*.tmp` en `.gitignore`.

- **Hallazgos NO arreglados (deuda consciente, registrada en handoff Paso 3):**
  - **Consider — alert_log UNIQUE traga auditoría**: `(subscription_id, bout_id, fired_at_epoch_hour)` es de la era fire-once; con D40 varios `update` (o `update`+`started`) del mismo sub/bout en la misma hora → 2º insert choca (IntegrityError→rollback) y el push queda enviado pero sin fila de auditoría. Propuesta: añadir `message_type` al UNIQUE.
  - **Consider — `POST /api/devices` upsert sin auth con ID de cliente**: quien conozca un `device_id` puede sobrescribir su `fcm_token` (secuestro de alertas). Aceptable MVP (UUID opaco) pero sin rate-limiting y `min_length=32` admite no-UUIDs. Propuesta: validación UUID v4 estricta.
  - **Nits**: `attempts` en `_log_alert` registra siempre el máximo aunque el push salga al 1er intento; `session` inyectada sin uso (noqa) en events; `downgrade()` de la migración recrearía ENUMs sin valores en PG (best-effort, irrelevante); `get_transition` en `state.py` posiblemente dead code; commit de 2.400 líneas demasiado grande — pedir tandas como commits en 7b.

- **Plan MVP Android consolidado en handoff** (qué falta para app funcional): Paso 0 Firebase (manual owner, ~30 min) → Paso 1 Fase 7b (la app, 3-5 sesiones, camino crítico = `AlarmScheduler` + verify-then-ring) → Paso 2 Fase 7c (Railway + EAS + smoke) → Paso 3 deuda review oportunista.

- **Verificación final**: **80 tests verdes** (78 + `test_device_header_is_case_insensitive` + `test_list_events_cache_only_applies_to_default_query`), ruff ✅, black ✅, mypy ✅ (37 ficheros).

- **Memorias actualizadas**: `handoff.md` (Sesión 13 + plan MVP por dependencias + estado global), `bitacora.md` (esta entrada). Commit + push a `dev`.

- **Pendiente para próxima sesión**: Firebase (owner) en paralelo; arrancar Fase 7b por el native module (`AlarmScheduler` + refactor `AlarmService` + permisos), después cliente FCM + pantallas.

## Sesión 14 — Plan pivot a Kotlin nativo puro (sin Expo/RN) para la app Android (2026-07-16)

- El owner preguntó si, teniendo Android Studio, se podía quitar Expo para simplificar el desarrollo. Análisis: la funcionalidad crítica del MVP (AlarmScheduler, AlarmService, AlarmActivity, bypass DnD, FCM) es Kotlin sí o sí — Expo solo cubría la capa de pantallas a cambio de mantener dos runtimes (JS + nativo), el bridge, Metro, Node y EAS (que ya dio problemas: build ERRORED por lock, colas ~2h free tier).
- **Decisión del owner: quitar Expo e ir a Kotlin nativo + Jetpack Compose.** D43 pendiente de registrar; Ajuste al plan: §7b/7c pendiente de reescribir en `fases.md`.
- Plan de ejecución consolidado en handoff: Paso 1 (scaffold Kotlin, smoke emulador), Paso 2 (`AlarmScheduler` D40), Paso 3 (Pantallas Compose restantes), Paso 4 (Tramo FCM + Redis), Paso 5 (Validación + deploy Railway).
- Coste asumido: iOS (Fase 7d, post-MVP) será rewrite SwiftUI en vez de reutilizar pantallas TS (la alarma iOS requería módulo Swift/AlarmKit nativo de todos modos).
- Hallazgo de entorno anotado (handoff Sesión 14) pero **sería verificado incorrecto en Sesión 15**: este PC *no* tenía Android Studio IDE, pero *sí* SDK Android portable + JDK 17 + AVD `pixel_6_api34` + JAVA_HOME/ANDROID_HOME/PATH configurados (instalados en Sesiones 10-11). No hace falta instalar Android Studio para compilar — `gradlew assembleDebug` corre con el SDK portable.
- Solo memoria: no se escribió código. La ejecución real del pivot quedó para la Sesión 15.

## Sesión 15 — Scaffold Kotlin Compose ejecutado + Home/EventDetail navegables + smoke emulador OK (2026-07-16)

- Owner pidió que en esta sesión se viera algo "parecido a lo que era la web en el emulador": Home con Avísame → pantalla de combates con nombres, fotos y datos de la API, selector de minutos de aviso. Se recalibró el alcance honestamente: el resultado entregable fue Home + EventDetail navegables con la card completa de combates y fotos, sin AlarmScheduler todavía (progración de alarma local será la próxima sesión).
- **D43 registrada en `decisiones.md`**: pivot a Kotlin nativo + Jetpack Compose, supersede el stack RN+Expo de D37 (sin tocar D37). Stack definitivo: Compose BOM 2024.12 + Kotlin 2.0.21 + AGP 8.7.3 + Gradle 8.11.1 + Retrofit 2.11 (converter oficial `kotlinx-serialization`) + Coil 2.7 + DataStore Preferences 1.1 + Navigation Compose 2.8 + Material3.
- **D44 registrada**: nota técnica del entorno "este PC: SDK Android portable sin IDE Android Studio (compilar vía `gradlew assembleDebug` desde CLI)". Corrige el handoff Sesión 14 que decía que el SDK no estaba. Aclara para futuros continuadores qué hay instalado y qué falta (solo el wizard GUI).
- **Renombrado `mobile/` → `mobile-expo/`** (preserva spike Expo en WD, refs en histórico git). Backup táctico de `.kt` a `Temp/spike-kt-ref/`.
- **Scaffold `mobile-kotlin/` a mano**:
  - `settings.gradle.kts`, `build.gradle.kts`, `gradle/libs.versions.toml` (version catalog).
  - Wrapper Gradle 8.11.1 (jar+scripts copiados de `mobile-expo/android/gradle/wrapper/`).
  - `debug.keystore` generado con `keytool` del JDK 17.
  - `app/build.gradle.kts` con Compose + DataStore + Retrofit + Coil + Navigation.
- **Código Kotlin Compose completo** para 2 pantallas con navegación:
  - `DespertarMeApp.kt` (Application: canal `IMPORTANCE_HIGH` + `setBypassDnd` — mismo del spike).
  - `MainActivity.kt` (single-activity + NavHost `home → event/{eventId}`).
  - `ui/theme/`: Color (`#E50914`, `#0A0A0A`) + Type (Inter sin embeber todavía) + Theme dark-first.
  - `ui/screens/HomeScreen.kt`: hero `drawable-nodpi/hero.webp` (extraído de la rama `web` del backend — cartel UFC 329 D36/D42) + veil degradado + botón "Avísame" (navega a EventDetail del próximo evento) + botón "Probar sonido" (arranca `AlarmService` portado del spike).
  - `ui/screens/EventDetailScreen.kt`: `LazyColumn` de combates. Cada `BoutCard` con: matchNumber + chip `cardSegment` + `weightClass` + `periods`; columnas rojo/azul con `AsyncImage` (Coil) para `headshot_url` + `name`; `FlowRow` de `FilterChip` para selector 5/10/15/30/60; botón "Avisarme" → `POST /api/subscriptions` con `X-Device-Id`; cambia a "Avisando ✓" tras suscripción; Snackbar "Alerta creada: X vs Y — N min".
  - `ui/viewmodel/EventDetailViewModel.kt` + `Factory` (inyección manual de `AppContainer`).
  - `data/remote/`: `DespertarApi` (Retrofit interface) + DTOs `@Serializable` + `DeviceIdInterceptor`.
  - `data/DeviceStorage.kt` (DataStore Preferences, UUID v4 persistente) + `AppContainer.kt` (OkHttpClient singleton, registro best-effort).
  - `alarm/AlarmService.kt` portado del spike a paquete `com.despertarme.app.alarm` (mismo `TYPE_ALARM` + `USAGE_ALARM` + `setBypassDnd` + `mediaPlayback` foreground validado Sesión 11).
- **`AndroidManifest.xml`** con `usesCleartextTraffic=true` (necesario para `http://10.0.2.2:8000/` en API 28+) + permisos `USE_EXACT_ALARM` + `USE_FULL_SCREEN_INTENT` + `RECEIVE_BOOT_COMPLETED` + los del spike.
- **3 iteraciones de `./gradlew assembleDebug`** hasta `BUILD SUCCESSFUL` — 3 fixes aplicados en el proceso:
  1. `signingConfigs.getByName("debug")` en lugar de `create("debug")` (AGP ya crea uno por defecto).
  2. Converter oficial Retrofit `com.squareup.retofit2:converter-kotlinx-serialization` (1.0.0 de Jake Wharton no exponía el import `retrofit2.converter.kotlinx.serialization.asConverterFactory`).
  3. Import `FlowRow` desde `androidx.compose.foundation.layout` + `@OptIn(ExperimentalLayoutApi::class)` (no en `androidx.compose.material3` como había puesto inicialmente).
  4. Extra: `Image(painterResource(R.drawable.hero), ...)` en HomeScreen en lugar de `AsyncImage(model: Painter?, ...)` (Coil rechaza Painter como model con `IllegalArgumentException`).
- **Backend SQLite levantado** con `cwd` en raíz del repo (no `src/` — si no, `.env` no se carga y cae a defaults Postgres asyncpg rechazado sin Docker). `alembic upgrade head` aplicado.
- **Smoke emulador `pixel_6_api34`** `adb reverse tcp:8000 tcp:8000` (puente emulador→host además de 10.0.2.2 AOSP nativo). APK debug 21.9 MB instalado. Primero crash FATAL (`IllegalArgumentException: Unsupported type: Painter`) — fixeado. Segundo crash por `ViewModel` sin factory (AGP no inyecta `AppContainer`) — fixeado con `EventDetailViewModelFactory`. Tercer intento: app arranca sin FATAL, Activity visible.
- **Smoke end-to-end verificado vía logs**:
  - `GET /health` → 200 OK.
  - `POST /api/devices` (curl simulación) → 201. `POST /api/subscriptions` → 201 (`edf42792...`). `GET /api/events/600059599` → 200 con 12 combates reales (Ezra Elliott vs Damien Anderson, etc.).
  - **Tráfico real de la app en `uvicorn.out`**: puerto 55980 realiza `POST /api/devices` + `GET /api/events` (registro + LaunchedEffect). Tras `adb shell input tap 540 2150` → `GET /api/events/600059599` desde puerto 56063 (navegación Home→EventDetail exitosa).
  - **SQLite verificado**: device `e57d6077-7ef4-4e68-bb99-8d9d8a2ae174` registrado por la app (platform=android, locale=es-ES). DataStore persiste el UUID.
- **Pendiente para próxima sesión** (Paso 2 de Fase 7b, camino crítico D40): `AlarmScheduler` (`AlarmManager.setAlarmClock()` a `estimated_start_at − lead_minutes`) + `AlarmReceiver` + verify-then-ring (fetch `GET /api/events/{id}` al disparar → sonar / reprogramar / silenciar) + `AlarmActivity` full-screen + `BootReceiver`. Esto convierte el botón "Avisarme" en una alarma local real que sonará a la hora estimada — hoy solo persiste la suscripción en BD pero no dispara sonido. Después pantallas restantes (Mis Alertas, Eventos lista, Ajustes) y tramo FCM.
- **Memorias actualizadas**: `decisiones.md` (D43 + D44), `fases.md` (§7b/7c reescritas con stack Kotlin real + checkboxes del Paso 1 marcados), `handoff.md` (esta sesión + corrección crítica "Android Studio IDE no está; SDK portable sí está"), `bitacora.md` (esta entrada). Commit final único pendiente.

## Sesión 15 (cont.) — Fixes visuales + bloqueo alarma por FCM (2026-07-16)

- Owner probó la app en emulador tras commits `c8efde3` (scaffold) + `c226107` (memorias Sesión 15). Reportó 4 issues: (1) botón "Avísame" no visible en Home (oculto bajo gesture nav bar por `enableEdgeToEdge` sin compensar insets), (2) hero de Home demasiado grande / recorta a los peleadores (`ContentScale.Crop` full-screen), (3) peleadores sin foto muestran círculo vacío (ESPN no resuelve headshot para debutantes/prelims), (4) tras darle back no podía volver a combates (consecuencia directa de #1 — sin botón visible, sin navegación).

- **Fixes aplicados (commit a055231):**
  - Home reestructurado en Column vertical con 2 zonas: hero `ContentScale.Fit` + `weight(1f)` arriba (poster completo, ambos peleadores visibles sin recortar) + zona inferior fija sobre `BackgroundDark` sólido con título + botones. Sin overlay degradado (sobraba cuando el hero no es full-screen).
  - `windowInsetsPadding(WindowInsets.safeDrawing)` aplicado al Column padre para que los botones no queden tras las barras del sistema.
  - `AthleteColumn` con placeholder de iniciales (mayúsculas, primera+última) sobre el color de la esquina (rojo/azul con alpha 0.40) cuando `headshot_url == null`. Si el nombre también es null, usa `Icons.Filled.Person`. Equivalente al SVG placeholder de la web (Sesión 5).
  - Build SUCCESSFUL (55s, solo warning cosmético `Icons.Filled.ArrowBack` deprecated). APK reinstalado. App arranca sin FATAL. Tap en zona inferior (540, 2050) dispara nueva navegación Home→EventDetail visible en `uvicorn.out` (puerto nuevo, `GET /api/events/600059599`).

- **Owner aceptó el Home como está**: "se quedará así la imagen, no es tan relevante en esta fase". El resto funciona.

- **Bloqueo alarma — redescubrimiento del objetivo central de la app:**
  - Owner pidió "la alarma tiene que funcionar en este v1" y aclaró: **"no es para que te avise a la hora que este programada la pecha, el objetivo de esta app era seguir en tiempo real los combates para cuando acabe el anterior avisarte exactamente cuando empieza el siguiente (el tiempo de antes que le pongas)"**.
  - Revisando `poller.py` y `decisiones.md` D40 confirmé que la app fue diseñada para exactamente eso: el backend hace polling de ESPN en vivo (cada 60s), cuando el combate previo transiciona `in→post`, recalcula `estimated_start_at` y envía push FCM `update` con el timestamp fresco a la app; la app recibe y reprograma la alarma local `AlarmManager.setAlarmClock()`. Sin FCM este bucle es imposible.
  - Un `AlarmScheduler` de un solo disparo con `bout.date` (lo que yo proponía) **no resuelve el caso de uso** — solo te avisa a la hora oficial, como cualquier calendador. Si el combate previo se alarga, la alarma suena antes de tiempo y no hay forma de corregirlo.
  - **FCM es el desbloqueante**: los push `update` son la única vía de que el backend avise a la app *"la estimación cambió, reprograma"*.

- **Botón "Probar sonido"**: owner pidió dejarlo por ahora ("para comprobar que funciona, como en el primer spike"). Se quitará cuando entre FCM y `AlarmScheduler` real. Por ahora sigue como debug manual que arranca `AlarmService`.

- **Decisión de cierre**: parar la sesión. La próxima arranca por setup Firebase manual del owner (~30 min en console.firebase.google.com): proyecto `despertarme`, service account key Python, `google-services.json` en `mobile-kotlin/app/`. Detalles en `handoff.md`.

- **Objetivo del producto grabado para futuras sesiones**: avisar X minutos antes de que un combate empiece realmente, siguiendo en vivo el combate previo y recalculando el inicio estimado en cada transición de estado. No es un calendador. La alarma local exacta (Android `setAlarmClock` / iOS AlarmKit D40) es la fuente de verdad del cuándo sonar, y el backend la mantiene fresca vía push FCM `update` con `estimated_start_at`. Verify-then-ring al disparar (D40). Bypass DnD obligatorio (validado Sesión 11).

- **Pendiente para próxima sesión**: (1) owner crea proyecto Firebase + service account key Python + `google-services.json` Android; (2) backend FCM ya funcionará una vez set `FCM_CREDENTIALS_JSON` en `.env` (código en `notifiers/fcm.py` desde Sesión 12 + fix Critical Sesión 13, solo falta la credencial); (3) cliente Android FCM `FirebaseMessagingService` que parsea `update|started|cancelled` y reprograma `AlarmScheduler`; (4) `AlarmScheduler` + `AlarmReceiver` + verify-then-ring + `AlarmActivity` full-screen + `BootReceiver`; (5) Redis `docker compose up -d` para desbloquear el poller.

- **Sin commits de código Kotlin en esta sesión-cierre**. Solo se va a commitear la actualización de memorias.


## Sesión 16 — Fase A plan MVP Android: entorno operativo en máquina javier.romero (2026-07-17)

- Primera sesión en la máquina nueva (`javier.romero`, Windows). Ejecutada como goal de OpenCode (plugin `/goal`, opencode-goal-plugin) con la Fase A de `memoria/plan-mvp-android-fable5.md` como objetivo. De paso se detectó que `/goal status` sin goal activo enruta el texto al modelo en vez de renderizar la salida canónica (limitación documentada del plugin: `command.execute.before` no intercepta del todo; las mutaciones de estado sí funcionan y las tools quedan read-only en ese turno).

- **Virtualización**: hipervisor activo (`hvservice` + `vmcompute` corriendo, WSL2 Ubuntu). El `VirtualizationFirmwareEnabled=False` de `Win32_Processor` era el falso negativo clásico con Hyper-V on (Windows corre virtualizado y no reporta el firmware). `emulator -accel-check` → "WHPX(10.0.26100) is installed and usable". HAXM no instalado (incompatible con Hyper-V, per plan).

- **Android Studio 2026.1.2.10** vía winget (UAC manual del owner). jbr embebido = OpenJDK 21.0.10.

- **SDK bootstrapeado 100% por CLI** (sin first-run wizard): cmdline-tools zip → `%LOCALAPPDATA%\Android\Sdk\cmdline-tools\latest`, `sdkmanager --licenses` aceptadas, instalados platform-tools 37.0.0 + platforms;android-34 + build-tools;34.0.0 + emulator 36.6.11 + system-images;android-34;google_apis;x86_64. Quirk: `Invoke-WebRequest` truncó el zip a 79 MB (fallo silencioso, "end of central directory" al extraer); `curl.exe -L -C -` lo completó a 136 MB. Preferir `curl.exe` para descargas grandes en esta máquina.

- **Env vars**: `ANDROID_HOME` (User) + platform-tools/emulator/cmdline-tools en PATH User. `JAVA_HOME` (Machine) ya apuntaba al JDK 21 de Microsoft (`C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot`) — válido ≥17, sin cambios. (El `java` del PATH sigue siendo un JRE 8 viejo pero gradlew usa `JAVA_HOME`.)

- **AVD `pixel_6_api34`** creado con avdmanager (Pixel 6, API 34, Google APIs x86_64) — mismo nombre que en la máquina pacor para reutilizar los comandos del handoff.

- **Build**: primera pasada falló solo en `:app:validateSigningDebug` (`app/debug.keystore` no versionado — se generó en el otro PC). Regenerado con keytool (androiddebugkey/android, RSA 2048). Segunda pasada: BUILD SUCCESSFUL en 1m 10s. `local.properties` creado con `sdk.dir` (gitignored).

- **Emulador**: AVD arrancado, "Windows Hypervisor Platform accelerator is operational", `adb devices` → `emulator-5554 device`, `sys.boot_completed=1`, Android 14. Warnings benignos: opengl32sw fallback a OpenGL del sistema, snapshot `default_boot` inexistente en primer boot.

- **Criterio de aceptación Fase A cumplido**: `gradlew assembleDebug` BUILD SUCCESSFUL + AVD sin errores de aceleración.

- `.gitignore` raíz: añadido `.opencode/goals/` (estado local del plugin `/goal`).

- **Pendiente**: Fase B (backend local: venv + `.env` SQLite + alembic + uvicorn + `adb reverse`) → Fases C/D (visual + pantallas) → Fase E (alarma v1). Fase G sigue bloqueada por Firebase manual del owner.

## Sesión 17 — Fases B+C+D plan MVP Android: backend local + bottom nav + 4 pantallas + E2E (2026-07-17)

- Goal de OpenCode agrupando Fases B, C y D de `plan-mvp-android-fable5.md` (decisión del owner: "agrupar b c y d").

- **Fase B — backend local operativo:**
  - venv (Python 3.12.10) + `.env` SQLite + paquete `avisador==0.1.0` ya existían de la Sesión 16 — verificado, no rehecho.
  - `alembic upgrade head` → head `f7a0001_devices`. uvicorn `--host 0.0.0.0` lanzado en background (`Start-Process` + `uvicorn.pid`).
  - **Quirk SSL corporativo (nuevo en esta máquina):** `GET /api/events` devolvía 503 con `CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain` — el proxy TLS de Inditex intercepta la conexión a ESPN y httpx/certifi no conocen la CA corporativa. **Fix sin tocar código del repo:** `pip install truststore` + `sitecustomize.py` en `.venv/Lib/site-packages/` con `truststore.inject_into_ssl()` (valida contra el almacén de certificados de Windows). ⚠️ El venv es gitignored: si se recrea, repetir el fix.
  - Criterios de aceptación: `POST /api/devices` → 201; `GET /api/events` → UFC Fight Night: Du Plessis vs. Usman; `GET /api/events/600059599` → 12 combates con nombres reales.

- **Fase D — cliente API completado:** `deleteSubscription` (`@DELETE /api/subscriptions/{id}`) + `listAlerts` (`@GET /api/alerts?limit=`) en `DespertarApi.kt`; DTO `AlertLogOut` en `Models.kt` (mapea `schemas.py::AlertLogOut` completo, incl. `fired_at_epoch_hour`, `notifier_response`, `payload`).

- **Fase C — NavigationBar Material3:** 4 destinos (Home/Eventos/Mis Alertas/Ajustes) con Material Icons Extended, seleccionado en `UfcRed` con indicador alpha 0.12, `containerColor = SurfaceDark`. `AppGraph` reescrito con `Scaffold(bottomBar=...)` + patrón estándar `popUpTo(findStartDestination){saveState=true} + launchSingleTop + restoreState`. La barra persiste también en EventDetail.

- **Fase D — 3 pantallas nuevas + 2 ViewModels:**
  - `EventListScreen` + `EventListViewModel`: `GET /api/events`, tarjeta con franja degradada roja + icono guante (sustituto de imagen — ESPN no sirve `image_url`, D42), nombre bold 17sp, fecha con punto rojo, chevron.
  - `SubscriptionsScreen` + `SubscriptionsViewModel`: activas (`GET /api/subscriptions`) con **nombres de peleadores resueltos** vía fetch del evento por `event_id` único (el backend solo devuelve ids; fallback "Combate #N"), punto verde de estado, papelera → `DELETE` + snackbar; historial (`GET /api/alerts`) con empty state.
  - `SettingsScreen`: cards Dispositivo (device_id monospace + timezone), Permisos (notificaciones vía `checkSelfPermission`, alarmas exactas vía `canScheduleExactAlarms`, iconos verde/rojo), Diagnóstico (toggle probar alarma).

- **Fase C — pulido BoutCard:** badge `cardSegment` con color (`main*` → rojo traslúcido, prelims → azul traslúcido; antes gris plano); chip "PRÓXIMO" blanco-sobre-rojo + `BorderStroke` rojo en el primer combate de la lista (el backend lista en orden cronológico — es el próximo en suceder). Fix warning `ArrowBack` → `Icons.AutoMirrored`. **Fuente Inter: evaluada y diferida** (binarios TTF en el repo sin beneficio claro en esta fase; retomar si el owner quiere identidad exacta con la web).

- **`AlarmService.ACTION_STOP` (hallazgo del smoke):** el service solo tenía `ACTION_START` — al probar la alarma desde Ajustes **no había forma de silenciarla desde la app** (el owner tuvo que pedir pararla; se paró con `adb shell am force-stop`). Añadido `ACTION_STOP` (`stopForeground(STOP_FOREGROUND_REMOVE)` + `stopSelf()`) + `stopTestAlarm()` en MainActivity + toggle "Probar/Parar sonido|alarma" en Home y Ajustes. Verificado: `dumpsys activity services` muestra el service arrancando y destruyéndose desde UI. La `AlarmActivity` de Fase E podrá reutilizar `ACTION_STOP` para el botón "Descartar".

- **Smoke E2E en emulador `pixel_6_api34`** (capturas revisadas en sesión):
  - Build `assembleDebug` SUCCESSFUL sin warnings.
  - Recorrido completo sin FATAL en logcat: Home (hero + bottom nav) → Eventos (tarjeta del evento) → EventDetail (PRÓXIMO + badges + selector) → "Avisarme" → `POST /api/subscriptions` 201 → Mis Alertas muestra "Anna Melisano vs Dione Barbosa · UFC Fight Night... · 15 min antes" → papelera → `DELETE` 204 + snackbar "Alerta cancelada" → empty state → Ajustes (permisos en verde, Device ID visible) → probar/parar alarma OK.
  - Quirk PowerShell documentado de paso: `adb exec-out screencap -p > file.png` corrompe el PNG (PS 5.1 convierte binario a texto) — usar `adb shell screencap /sdcard/x.png` + `adb pull`.

- **Pendiente próxima sesión:** Fase E (alarma v1 un solo disparo: `AlarmScheduler` + `AlarmReceiver` + verify-then-ring básico + `AlarmActivity` + `BootReceiver` + Doze) → Fase F (validación MVP) → Fase G bloqueada por Firebase manual del owner.

## Sesión 18 — Fase G: modelo de alarma revisado D45 (revisión tras grilling con el owner) (2026-07-17)

- **Contexto:** el owner pidió revisar el modelo de alarma; la Sesión 17 había cableado FCM pero con pre-programación al suscribir basada en el `bout.date` oficial de ESPN. El owner explicó con un ejemplo concreto que quería **NO crear alarma al suscribir**, sino solo cuando el backend detecta datos reales del combate previo (transiciones `pre→in` o `in→post`). Tras grilling iterativo en plan mode (6 rondas de preguntas), se refinó el modelo D45.

- **Decisiones del owner (D45):**
  - Cushion **siempre +1 min** sobre el trigger calculado (evita que `setAlarmClock` con timestamp "ahora mismo" no suene).
  - Lead 30: suena al recibir primer push (previo `pre→in`) + cushion 1 min (~29-39 min aviso).
  - Lead 10/15: suenan juntos al acabar el previo (~9 min aviso, "pequeña mentira para el usuario, para que piense que hay más variedad").
  - Lead 5: suena ~4 min después de que acabe el previo.
  - Lead 60: ELIMINADO por "demasiado difícil de predecir".
  - Sin fallback a la fecha oficial de ESPN (decisión del owner: "asumo el riesgo" si FCM no entrega).
  - `BUFFER_INTERCOMBATE_SECONDS` pasa de 300 a 600 (10 min reales entre combates, confirmado por el owner).
  - Ring-once: flag `PendingAlarm.fired` se marca cuando `AlarmReceiver` se dispara. Pushes FCM posteriores para el mismo bout se ignoran.
  - Backend **NO envía push `update` cuando `prev_state == "pre"`** (sería la fecha oficial de ESPN sin datos reales — programaría la alarma prematura).

- **Cambios backend:**
  - `src/app/engine/poller.py`: guard D45 — si `prev_state == "pre"` → `return False` (no pushear). `estimated_start_at` ahora es `str(int(estimate.start_at.timestamp() * 1000))` (epoch millis, no ISO string).
  - `src/app/scheduler.py`: añadido `EstimatorEngine(EstimatorConfig(buffer_intercombate_seconds=settings.buffer_intercombate_seconds))` wired al `Poller()`. Antes usaba `EstimatorConfig` default hardcodeado (300s), ignorando el `.env`.
  - `.env` + `.env.example`: `BUFFER_INTERCOMBATE_SECONDS=300` → `600`.
  - `tests/test_poller.py`: 3 tests ajustados (guard pre-vs-push → 0 pushes esperados; epoch millis → parse con `datetime.fromtimestamp(val/1000, tz=UTC)`). 80/80 tests verdes.

- **Cambios Android (Kotlin):**
  - `PendingAlarm.kt`: añadido campo `fired: Boolean = false`.
  - `EventDetailViewModel.subscribe()`: eliminada la llamada a `AlarmScheduler.schedule()`. Solo persiste `PendingAlarm(triggerAtMillis=0L, fired=false)` via `PendingAlarmStorage.put()`.
  - `EventDetailScreen.kt`: `LEAD_OPTIONS = listOf(5, 10, 15, 30)` (quitado 60).
  - `DespertarMeFirebaseService.handleUpdate()`: reescrito con lógica D45:
    - Si `existing.fired` → ignora (ring-once).
    - Si `lead>=30 && triggerAtMillis>0` → ignora (programa solo en el primer push).
    - Si `lead>=30` → `trigger = now + 60_000` (suena ~1 min cushion).
    - Si `lead<30` → `trigger = max(now+60_000, estimatedStartMs - lead*60_000 + 60_000)`.
  - `DespertarMeFirebaseService.cancelAlarmAndNotify()`: marca `fired=true` antes de cancelar.
  - `AlarmReceiver.kt`: reescrito — sin verify-then-ring (ya no necesario). Marca `fired=true` al disparar, arranca `AlarmService` + `AlarmActivity`.
  - `SubscriptionsViewModel.cancel()`: sin cambios (ya cancela alarma local vía `AlarmScheduler.cancel()`).
  - Build: `gradlew assembleDebug` → BUILD SUCCESSFUL.

- **Smoke parcial (sin Docker/Redis):** el poller del backend no puede correr (Redis requiere Docker Desktop, no disponible en esta máquina). El humo se limita a:
  - Compilación backend (ruff clean, pytest 80/80 ✅).
  - Compilación Android (assembleDebug BUILD SUCCESSFUL ✅).
  - Verificación lógica via tests del poller (guard D45, epoch millis).
  - Quedan pendientes de smoke real: suscribir → esperar push real del poller → alarma programada → suena.

- **Hallazgos técnicos en esta sesión:**
  1. `settings.buffer_intercombate_seconds` estaba definido en config.py pero nunca se enrutaba al `EstimatorEngine` — usaba siempre el default hardcodeado 300s.
  2. `AlertPayload.estimated_start_at` es `str | None` — el poller mandaba `estimate.start_at.isoformat()` (ISO datetime), que Android no puede parsear con `toLongOrNull()`. Cambiado a `str(int(epoch_millis))` para simplicidad en Android.
  3. `myep` da exit 1 sin output en esta máquina — posible venv corrupto o dependencia mypy faltante (no investigado; ruff y pytest cubren).

- **Memorias actualizadas:** `handoff.md` (nueva sesión), `bitacora.md` (esta entrada), `fases.md` (Fase G marcada + links D45), `decisiones.md` (D45), `plan-mvp-android-fable5.md` (Fase E/G actualizadas).

- **Pendiente próxima sesión:** arrancar Docker Desktop (`docker compose up -d`) para tener Redis → poller activo → primer smoke E2E con evento real de ESPN → validar ring-once y Doze. Validación en hardware físico del owner.

## Sesión 18 (cont.) — Firebase + Docker + smoke E2E Fase G verificado en emulador (2026-07-17/18)

- **Firebase setup completado por el owner:** proyecto `despertarme-73d00` en `console.firebase.google.com`. Service account JSON + `google-services.json` generados. Owner soltó los dos ficheros en la raíz del repo; yo los renombré/moví a `.firebase-service-account.json` (root, gitignored) y `mobile-kotlin/app/google-services.json` (commiteable). Verificado: `project_id=despertarme-73d00`, `package_name=com.despertarme.app` ✓.
- **Backend FCM verificado:** `build_notifier()` devuelve `FcmNotifier` con los credenciales nuevos. Smoke Python con token fake → FCM respondió `InvalidRegistration` (esperado — confirma que las credenciales están autenticadas y el pipeline cableado, solo faltaba token real).
- **Android Firebase wired:** plugin `com.google.gms.google-services:4.4.2` + `firebase-messaging-ktx:24.1.0` añadidos a `libs.versions.toml` + `build.gradle.kts` (root + app). Build SUCCESSFUL con `processDebugGoogleServices` task ejecutándose.
- **Docker Desktop + Redis arrancados:** `docker compose up -d redis` (Postgres no necesario en dev, seguimos con SQLite). Poller del backend corriendo cada 60s, contactando ESPN. Las 7 suscripciones de smoke previas apuntan a `bout_id=401566093` que ya no existe en la card de ESPN — el poller las salta con warning "Combate 401566093 no encontrado" sin crashar (comportamiento correcto y resiliente).
- **Emulador + APK + FCM token real:**
  - `pixel_6_api34` arrancado (boot completo en 39s).
  - APK 21.8 MB instalado (con `google-services.json` ya enlazado).
  - Permiso `POST_NOTIFICATIONS` concedido.
  - `FirebaseMessagingService.onNewToken()` disparó → token real `e_f7hyAYQIWcSWwfZLcoah:APA91bGddMfTx_ZpaiSVTtLJ...` persistido en DataStore + registrado con el backend vía `POST /api/devices` upsert. Logcat: "Nuevo FCM token: ..." + "FCM token registrado con el backend".
  - **Impresión:** Firebase funciona en emulador con imagen `google_apis;x86_64` (no necesita Google Play, solo Google Play Services — incluido en la system image).
- **Smoke `POST /api/devices/me/test-alarm` E2E OK** (sin endpoint debug, pasa directo por el endpoint estándar del backend):
  - Backend envió push FCM `fire` con message_id `projects/despertarme-73d00/messages/0:1784323051075181%bde80ad8f9fd7ecd` (entrega confirmada por Firebase).
  - App recibió `FCM message type=fire` (logcat 21:17:29).
  - `Background started FGS: Allowed ... intent: ACTION_START cmp=com.despertarme.app/.alarm.AlarmService` → AlarmService foreground arrancado.
  - `FlashNotifController: startFlashNotification: type=2, tag=alarm` → notificación de alarma creada.
  - `WindowManager: ... topActivity=ComponentInfo{com.despertarme.app.alarm.AlarmActivity}` → pantalla full-screen abierta.
  - `AudioTrack: stop(15): called with 91283 frames delivered` → sonido TYPE_ALARM reproduciéndose.
  - **Pipeline completo backend → FCM → app → sonido → pantalla verificado.**
- **Smoke endpoint debug `simulate-transition`** (temporal, creado y borrado en esta sesión):
  - Creado `src/app/api/routes/debug.py` + registro en `main.py` gateado por `if settings.app_env == "development"`.
  - Owner creó suscripción nueva desde la app: `bout_id=401889642` (combate #12, Women's Flyweight, prelims), `lead_minutes=5`, device `e57d6077...`.
  - Llamada: `POST /api/debug/simulate-transition?bout_id=401889642&estimated_start_in_minutes=10` a las 22:12:31.
  - Backend mandó push FCM `update` con `estimated_start_at = epoch_millis(now + 10min)`.
  - App recibió `FCM message type=update` (logcat 22:12:31) → `handleUpdate()` leyó `PendingAlarm(lead=5, fired=false, triggerAtMillis=0)` → calculó `trigger = max(now+60s, est-5min+60s) = now+6min` → `AlarmScheduler.schedule(trigger=now+6min)`. Logcat: "Alarma programada: bout=401889642 trigger=1784326712522 (sonará en 361s)".
  - `dumpsys alarm` confirmó: `RTC_WAKEUP #7: Alarm{986b0ee ... com.despertarme.app} tag=*walarm*:com.despertarme.app.action.ALARM_FIRE`.
  - **A las 22:18:32 (6 min 2 s después del push)** → `AlarmReceiver: Alarma disparada y fired=true marcado para bout=401889642`.
  - `Window{... AlarmActivity}: Setting back callback` → AlarmActivity abierta sobre lockscreen.
  - `Displayed com.despertarme.app/.alarm.AlarmActivity for user 0: +519ms` → activity visible.
  - `AudioTrack: stop(16): called with 91283 frames delivered` → TYPE_ALARM reproduciéndose.
  - **Pipeline D45 completo verificado end-to-end en emulador**: suscripción backend → debug simulate (push `update` con epoch millis) → handleUpdate con cushion always +1 min → AlarmScheduler.setAlarmClock → 6 min espera → AlarmReceiver dispara → AlarmActivity full-screen + sonido → marca `fired=true` (ring-once).
  - Alarma silenciada con `adb shell am force-stop com.despertarme.app` (el service no es exported, no se podía parar con `am startservice STOP_ALARM` desde adb; dentro de la app el botón "Descartar" de `AlarmActivity` sí lo para).
- **Limpieza y verificación final:**
  - `src/app/api/routes/debug.py` borrado.
  - Bloque `if settings.app_env == "development"` (con import y registro del router debug) borrado de `main.py`.
  - `ruff check src tests` ✓.
  - `pytest` 80/80 verdes tras el borrado.
- **Hallazgos técnicos de la smoke:**
  1. El primer push `update` a las 22:09:30 resultó en un trigger de 81989s (~22h) en vez de ~6min — probablemente el `PendingAlarm` storage estaba corrupto de una prueba previa (o se calculó contra un `EstimatedStart` viejo). El segundo push a las 22:12:31 ya calculó correctamente 361s. **Confirmado:** la lógica cushion es correcta cuando el PendingAlarm storage está limpio.
  2. `AlarmService` no exported → `adb shell am startservice ACTION_STOP` devuelve "Permission Denial: Accessing service ... not exported from uid". Esto es correcto seguridad-wise. Para parar la alarma desde ADB: `am force-stop com.despertarme.app` (mata la app entera) — dentro de la app el botón "Descartar" usa `startService(ACTION_STOP)` que sí está permitido.
  3. `FirebaseInitProvider` arranca antes que `Application.onCreate` (estándar de ContentProvider) → `onNewToken` puede dispararse antes de que `DespertarMeApp.container` esté listo. Fix: persistir el token en `DeviceStorage` directamente desde el servicio FCM, y luego `ensureRegistered()` en `MainActivity.onCreate` lo recoge. El companion `app.isContainerReady` evita NPE.
  4. Pushes FCM data-only entregados a app en background en emulador API 34 Google APIs — confirmado (la app estaba en background cuando llegó el push `update` y el `FirebaseMessagingService.onMessageReceived` lo procesó correctamente).
- **Próximo hito:** UFC Fight Night: Du Plessis vs Usman el 18 de julio (mañana, hoy ~00:30 del 18 ya). Prelims a las 23:00 CEST, main card a las 02:00 CEST del 19. **Suscribirse a un combate actual desde la app** (no las antiguas con bout_id obsoleto) y dejar el backend corriendo para que el poller detecte transiciones reales de ESPN. Eso validará el flujo completo sin simulación.

## Sesión 19 — Polishing pre-Play Store (2026-07-18)

- El owner preguntó cuánto quedaba para terminar la app. Tras revisión completa del código de `mobile-kotlin/` (27 ficheros Kotlin + manifest + resources) se confirmó que **el código de features está terminado** desde Sesión 18 (Fase G completada con pipeline FCM end-to-end verificado en emulador). Esta sesión fue de pulido pre-Play-Store, no de features.
- **Icono de launcher propio** — adaptive icon vectorial (sin PNGs por densidad, `minSdk=26` lo permite): `res/drawable/ic_launcher_background.xml` (fondo rojo `#E50914`) + `res/drawable/ic_launcher_foreground.xml` (Material `ic_alarm` blanco en safe zone de 108dp) + `res/mipmap-anydpi-v26/ic_launcher.xml` + `ic_launcher_round.xml`. `AndroidManifest.xml` actualizado: `@android:drawable/sym_def_app_icon` reemplazado por `@mipmap/ic_launcher` + `@mipmap/ic_launcher_round`.
- **PNG Play Store** — `scripts/gen_playstore_icon.ps1` commiteable (PowerShell + `System.Drawing`) genera `mobile-kotlin/app/src/main/playstore-icon.png` 512×512 (fondo rojo + reloj blanco). Placeholder, mejorables con logo del owner.
- **Limpieza de código menor:** 3 imports sin usar borrados de `AlarmActivity.kt` (`kotlin.time.Duration.Companion.minutes`, `kotlin.time.DurationUnit`, `kotlinx.coroutines.runBlocking`); dead code `val attrs` + `@Suppress("unused")` borrado de `DespertarMeApp.kt`; comentario stale "until the FCM tramo arrives" actualizado en `AppContainer.kt` (FCM está wired desde Sesión 18, el placeholder sigue siendo válido para el caso pre-`onNewToken`).
- **Deuda documental de Sesión 18 cerrada en `memoria/fases.md`**: Paso 4 (Tramo FCM) y AlarmScreen marcados `[x]` con notas "(Sesión 18: ...)".
- **Decisiones del owner explícitas en esta sesión:** (a) icono vectorial rojo + PNG 512 para Play Store, (b) sonido custom `alarm.ogg` pospuesto al post-MVP, (c) release keystore + `baseUrl` per buildType + ProGuard pospuestos al tramo pre-Play-Store final (no bloquean test local en emulador).
- **Pendiente:** validación con evento UFC real (hoy 18 jul), hardware físico del owner, Doze, Railway, release build config + Play Store listing.

**Decisión post-sesión (2026-07-18):** el owner decidió que el test en móvil físico se hará vía Railway (Opción C), no con `adb reverse` + `10.0.2.2` del emulador. Esto implica: (1) crear cuenta Railway + deploy, (2) cambiar `baseUrl` en `AppContainer.kt` de `http://10.0.2.2:8000/` a la URL HTTPS de Railway, (3) recompilar APK debug, (4) instalar en móvil vía `adb`. Railway se convierte en el prerrequisito bloqueante para el test en hardware físico. El cambio de `baseUrl` (~1 línea) y la recompilación se ejecutan apenas el owner dé la URL. Sin Railway, el móvil físico no puede contactar al backend porque `10.0.2.2` solo resuelve en emulador AOSP.

## Sesión 20 — Railway deploy operativo. baseUrl cambiado a URL pública. APK lista para test en hardware físico (2026-07-18)

- **Backend desplegado en Railway:** `https://despertarme-production.up.railway.app`. `/health` 200 (`{"status":"ok","env":"production"}`), `/api/events` devuelve datos reales de ESPN (UFC Fight Night Du Plessis vs Usman, 12 combates con headshots), `/api/events/600059599` con `previous_bout_id` derivado server-side (E4 verificado: bout #11 → previous=401889642). Configurado `FCM_CREDENTIALS_JSON` + `SCHEDULER_ENABLED=true` → poller 24/7 corriendo en Railway.
- **3 fixes aplicados a la migración `f7a0001_devices`** (fallaba en Railway PG virgen sin log output, OOM probable en free tier):
  - (a) Añadido `if_exists=True` a los 5 `op.drop_table()` (no-idempotente → idempotente). En PG virgen son no-ops. 
  - (b) Eliminado bloque `sa.Enum(name="user_role").drop()` (innecesario en PG virgen; `subscription_status` y `alert_status` se reciclan en el nuevo schema).
  - Commits `f32d502` + `50aa62f`.
- **Fix de `railway.json`:** (a) `healthcheckTimeout` de 120 → 300s (Railway free tier lento). (b) `startCommand` eliminado (Railway no soporta shell builtins como `set`, `exec`; usa CMD del Dockerfile). (c) `--log-level debug` añadido al CMD del Dockerfile para diagnóstico. Commit `6164820`.
- **`.dockerignore` creado** (62 líneas): excluye `.venv/`, `mobile-kotlin/`, `mobile-expo/`, secrets, logs, caches. Commit `9a7b911`.
- **Root cause del primer healthcheck failure:** la variable `DATABASE_URL` en Railway tenía un espacio al final (SQLAlchemy rechaza URLs con whitespace). Tras corregir, deploy pasó a "Running".
- **`baseUrl` en APK:** `AppContainer.kt:40` cambiado de `http://10.0.2.2:8000/` a `https://despertarme-production.up.railway.app/`. APK debug recompilada (BUILD SUCCESSFUL, 23.1 MB).
- **Nota:** el Railway deploy tomó varios intentos (3 errores distintos: ENUM-drop bug en migración, OOM del container por drops  en `if_exists`, espacio en DATABASE_URL). La combinación de estos 3 fixes + el `.dockerignore` resuelven todos los casos (deploy fresco, PG nueva o existente).
- **Pendiente próxima sesión:** validación con evento UFC real (hoy, prelims 23:00 CEST, main card 02:00 CEST), hardware físico del owner, Doze, release keystore + Play Store listing.
- **Smoke emulador con APK Railway:** APK instalada y arrancada en `pixel_6_api34` (pid 4546). App arrancó sin FATAL: `FirebaseApp initialized`, `FirebaseInitProvider successful`, `MainActivity displayed`. La APK contacta directo a Railway (`https://despertarme-production.up.railway.app`) — ya no necesita `adb reverse` ni `10.0.2.2`. Railway API verificada desde el emulador vía curl (`POST /api/devices` responde 422 con campos requeridos, confirma conectividad). Los logs de la app (`Log.i("DespertarMe", ...)`) no se capturaron en logcat por buffer limitado del AVD, pero la ausencia de FATAL + FirebaseInit OK + Railway reachable confirman que la app funciona. APK debug 23.1 MB lista para instalar en el móvil físico del owner.

## Sesión 21 — Diagnóstico FCM en hardware físico: no hubo error, pipeline verificado end-to-end (2026-07-21)

- **Contexto:** el owner reportó que la app no recibió pushes FCM en el móvil físico durante el evento UFC Fight Night: Du Plessis vs Usman del 18-jul. Sin acceso adb/logcat en el dispositivo, se diagnosticó remotamente desde la API de Railway + logs del backend. La sesión fue exclusivamente de diagnóstico (cero cambios de código).

- **Fase 1 — Verificación de salud del backend:**
  - `curl https://despertarme-production.up.railway.app/health` → `{"status":"ok","env":"production"}`.
  - `GET /api/events` → 1 evento: UFC Fight Night Ankalaev vs Guskov (25 jul 2026, 13:00 UTC). ESPN accesible.
  - 9 endpoints REST documentados en `/openapi.json` operativos.

- **Fase 2 — Revisión de logs del 18-jul en Railway:**
  - `grep "Notifier activo"` → `FcmNotifier (push reales)` — el backend usaba FCM real, no DummyNotifier.
  - `grep "Push"` → **13 pushes enviados** el 18-jul a device `3d9ef804`:
    - Suscripción `f538c874`: 1 `update` (19:17 UTC) + 1 `started` (21:00) + 1 `cancelled` (21:21).
    - Suscripción `b28e2de9`: 10 `update` (21:22→21:38) + 1 `started` (21:39) + 1 `cancelled` (22:12).
  - Cero errores de FCM en los logs. Firebase aceptó los 13 mensajes.
  - `grep "Job PollerScheduler"` → poller corriendo cada 60s sin interrupción, sigue activo hoy (2026-07-21).

- **Fase 3 — Diagnóstico del device del móvil físico:**
  - El owner obtuvo el `device_id` de la app en Ajustes: **`5c20fa0b-2ad2-4726-8b5e-cf1d757e8047`**.
  - `GET /api/subscriptions` con `X-Device-Id: 5c20fa0b...` → **`[]`** (sin suscripciones activas).
  - **Conclusión:** el device `3d9ef804` de los logs NO es el móvil físico. Es el emulador `pixel_6_api34` de la Sesión 18 (cada instalación genera un UUID distinto). Las suscripciones y pushes del 18-jul estaban en el emulador, no en el móvil.

- **Fase 4 — Prueba de fuego con test-alarm:**
  - `POST /api/devices/me/test-alarm` con `X-Device-Id: 5c20fa0b...` → `{"success":true, "message_id":"projects/despertarme-73d00/messages/0:1784643153549088%..."}`.
  - **La alarma sonó en el móvil físico.** Pipeline FCM backend→Firebase→móvil→`AlarmService`+`AlarmActivity` verificado end-to-end en hardware.

- **Fase 5 — Creación de suscripción real y verificación del poller:**
  - El owner creó suscripción desde la app del móvil: `POST /api/subscriptions` → 201 Created, `id=455062f2`, `bout_id=401898030`, `event_id=600059667`, `target_match_number=13`, `lead_minutes=5`, `status=active`.
  - El poller procesó la suscripción en el siguiente ciclo (14:16:08 UTC, 21-jul): envió push `update` al device `5c20fa0b`.
  - `GET /api/alerts` → 1 alerta registrada: `message_type=update`, `estimate_start=2026-07-25T13:00+00:00`, `reason="no hay combate previo; fecha programada"`, `notifier_response` con message_id real de Firebase.
  - **El push `update` fue entregado al móvil.** La app programó `setAlarmClock` en silencio (los pushes `update` no hacen sonar la alarma, solo programan el despertador).

- **Fase 6 — Hallazgo sobre `prev=None`:**
  - El combate suscrito (match 13 del evento 600059667) es el primero de la tarjeta. La card probablemente tiene 13 combates (matchNumber 13→1), y match 14 no existe → `prev is None` en el poller.
  - En este caso, el `EstimatorEngine` cae a la fecha oficial de ESPN como estimación (`card.bout.date`). Es el **único caso** donde se usa la hora programada (decisión explícita del owner). Para combates con previo real (match 1-12), la estimación se recalcula con el estado en vivo del combate previo (D18/D45).
  - La guarda D45 (`skip push si prev está en "pre"`) solo aplica cuando `prev is not None` — correcto, porque si no hay previo no hay nada que esperar. El poller envía el push inmediatamente con la fecha oficial.

- **Veredicto final:**
  - **No hubo ningún error.** El backend, el poller, FCM y la app funcionaron correctamente el 18-jul y hoy.
  - Las suscripciones del 18-jul estaban en el emulador (`3d9ef804`), no en el móvil (`5c20fa0b`). El móvil no podía recibir pushes porque no era destinatario de ninguna suscripción.
  - FCM entrega al hardware físico verificado con: (a) test-alarm (sonó), (b) push `update` del poller (entregado, message_id real en alert_log).
  - El pipeline está operativo end-to-end: Railway → Firebase → móvil → `handleUpdate` → `setAlarmClock`.

- **Pendientes para la próxima sesión:**
  1. **Validación con evento real** — UFC Fight Night: Ankalaev vs Guskov, 25 julio 2026, 13:00 UTC. El poller detectará transiciones ESPN del combate previo (match 14, o match 12 si la card es invertida) → push `update` a `5c20fa0b` → `setAlarmClock` → alarma suena ~4 min antes del combate objetivo (lead 5 − cushion 1 min). Si match 14 no existe, la alarma ya está programada con la fecha oficial de ESPN (push `update` del 21-jul 14:16 UTC).
  2. **Validación Doze** — `adb shell dumpsys deviceidle force-idle` + verificar `setAlarmClock` despierta.
  3. **Release keystore + Play Store** — cuenta Google Play ($25) + listing + AAB firmado.

- **Memorias actualizadas:** `handoff.md` (Sesión 21 como punto de entrada), `bitacora.md` (esta entrada), `fases.md` (checkboxes de validación hardware marcados).

---

## Sesión 22 — Sync de repo + plan de dogfooding Android+iOS (solo memorias, cero código) (2026-07-21)

- **Contexto:** el owner pidió traer todos los cambios del repo y ponerse al día. El `dev` local estaba parado en Sesión 17 (`d9d9105`) mientras `origin/dev` había avanzado con historia reescrita hasta Sesión 21 (`18095f3`). Tras confirmar que el contenido de los commits locales existía igual (mismos mensajes, distinto SHA) en el remoto, se hizo `git reset --hard origin/dev`.

- **Análisis del estado del MVP:** el owner preguntó si, fuera de la validación pendiente, el MVP es funcional, y qué haría falta afianzar antes de empezar iOS. Se repasó `fases.md`, `decisiones.md` y `plan-mvp-android-fable5.md` para separar deuda técnica bloqueante de la que solo aplica a publicación (Play Store/App Store, diferida explícitamente por el owner en esta sesión: "por ahora queremos seguir probando la aplicación bien nosotros y tener MVPs estables en nuestros dispositivos... antes de empezar a publicar").

- **Hallazgo nuevo (no documentado en sesiones anteriores):** revisando `src/app/notifiers/fcm.py::FcmNotifier.send()` se confirmó que el mensaje FCM se construye con `android=AndroidConfig(priority="high")` pero **sin `ApnsConfig`**. Un push data-only a un token iOS necesita explícitamente `apns-priority: 5` + `content-available: 1` para despertar la app en background — sin este fix, los pushes `update`/`started`/`cancelled` probablemente no llegarían de forma fiable a un cliente iOS. Bloqueante para cualquier prueba real en iOS, no descubierto hasta ahora porque nunca se había planificado el cliente iOS en detalle.

- **Investigación de membership Apple Developer** (`webfetch` a `developer.apple.com/support/compare-memberships`, verificado 2026-07-21): la cuenta gratuita ("Personal Team") permite testing on-device pero:
  - Certificados/perfiles de aprovisionamiento **caducan a los 7 días**.
  - **Sin ad-hoc distribution** ni **TestFlight** (ambos exclusivos del Programa de pago, $99/año).
  - "Advanced app capabilities and services" aparece solo en la columna de pago — riesgo real de que AlarmKit/Push Notifications avanzados lo requieran.

- **Restricción de entorno del owner:** solo tiene acceso a un Mac en la nube (proveedor sin decidir), no un Mac físico — esto descarta el flujo estándar de Xcode (emparejar el iPhone por USB a la máquina donde corre Xcode). Se propuso una combinación viable sin Mac físico: **GitHub Actions (`macos-14` runner)** para compilar (headless, sin necesitar login de Apple ID) + **AltStore/AltServer** (AltServer soporta host Windows) para firmar/instalar/refrescar el `.ipa` en el iPhone del owner desde este mismo PC, sin pasar nunca por una sesión interactiva de Xcode.

- **Plan documentado en `memoria/plan-mvp-ios.md`** (nuevo fichero, añadido al índice de `AGENTS.md` vía `scripts/gen_memoria_index.py`):
  1. Pista Android (compañero): validación con evento real 25-jul + Doze + sideload del APK + prueba multi-dispositivo.
  2. Fix de backend: `ApnsConfig` en `FcmNotifier.send()`.
  3. Fase 0 — spike de riesgo iOS: proyecto Xcode mínimo + CI GitHub Actions + AltServer, probando aisladamente AlarmKit y Push Notifications con Apple ID gratuita antes de comprometerse a construir las 5 pantallas completas. Condiciona la decisión de pagar el Programa Apple Developer al resultado del spike.
  4. Fase 2 (condicionada): MVP iOS completo (rewrite SwiftUI, D43) replicando el alcance de Android.
  5. Explícitamente fuera de alcance: Play Store/App Store, hardening de seguridad de `X-Device-Id`, fix del UNIQUE de `alert_log`, validación estricta de UUID en `DeviceCreate`.

- **Memorias actualizadas:** `handoff.md` (Sesión 22 como punto de entrada), `bitacora.md` (esta entrada), `AGENTS.md` (índice regenerado), `memoria/plan-mvp-ios.md` (nuevo).
