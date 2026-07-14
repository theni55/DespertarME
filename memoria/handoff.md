# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

---

## Última sesión

**Fecha:** 2026-07-13 · **Sesión 7 — Pivot a app móvil (D37/D38)**

**Contexto:** el owner decidió un cambio de rumbo: **dejar la web apartada**
y centrar el desarrollo en una app móvil (Android primero, iOS después).
Antes de ejecutar, se realizó una fase de planificación con preguntas
estructuradas que resolvió las decisiones de alto nivel (D37).

**Decisiones confirmadas (D37):**
- **Stack app**: React Native + Expo (TypeScript) con dev builds EAS.
- **Modelo**: sin cuentas de usuario. El actor es un `Device` (FCM token).
- **Notificaciones**: push FCM tipo despertador (bypass DnD, IMPORTANCE_HIGH,
  foreground service con STREAM_ALARM, full-screen intent).
- **Web**: web de usuario + landing **congeladas**. Admin web **refactorizado**
  a vista de devices.
- **Deportes v1**: solo UFC (lo ya integrado). Boxeo/Tenis diferido.
- **Backend**: Railway + Firebase FCM. Railway deploy ya planeado (D33).

**Qué se hizo en esta sesión:**
- Instaladas skills `grill-me` y `grilling` desde `mattpocock/skills` en
  `.opencode/skills/` (D38).
- Memorias actualizadas: `decisiones.md` (D37, D38), `fases.md` (Fase 6
  congelada, Fase 7 añadida), `handoff.md` (nuevo estado y sesión),
   `bitacora.md` (entrada de la sesión).
- **Split de ramas completado**: rama `web` creada desde `dcf62f8` como
  archivo congelado de la era web (pusheada a origin). `main` limpiada:
  `src/app/web/` eliminado (~2500 líneas HTML/CSS/Jinja2), `main.py`
  reducido a API-only (solo FastAPI + health + lifespan + routers REST),
  `pyproject.toml` sin `jinja2` ni `python-multipart`. 64 tests verdes
  (72 − 8 web). 2 commits en main: `d65f369` (skills + D37/D38) y
  `849ddd3` (web archival + cleanup).
- **Rama `web` verificada como auto-contenida**: smoke test en vivo —
  checkout web, uvicorn, y todos los endpoints responden 200: `/health`,
  `/` (landing con "Avísame"), `/admin/login`, `/app/login`, CSS/fonts/hero.
  Se levanta sola solo con `git checkout web` + `pip install -e .[dev]` +
  `alembic upgrade head` + `uvicorn app.main:app --reload`.
- **Grilling completado**: 17 decisiones de implementación resueltas con
  el owner vía `grilling` skill (`mattpocock/skills`). Plan de Fase 7
  consolidado en `decisiones.md` (D37 ampliado) y `fases.md` (Spike + 7a +
  7b + 7c + 7d detallado). PR #5 creado para sync `main` → `dev`.

**Pendiente tras el grilling:**
- Cerrar la sesión de grilling con todas las decisiones de Fase 7a y 7b
  cerradas.
- Crear skill `ship-polished-ui` (tarea pospuesta de la Sesión 6) — será
  útil durante Fase 7b para el diseño de la app.
- Arrancar Fase 7a (backend: device model + JSON endpoints + FCM notifier).

**Ramas:** la web congelada vive en la rama `web` (snapshot del último commit
de la era web, `dcf62f8`). `main` es ahora la rama de desarrollo de la app
(backend API-only + futuro `mobile/`). Para consultar o ejecutar la web:
`git checkout web` y levantar con `uvicorn app.main:app --reload`.

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
| Fase 5 — VoiceNotifier real (Twilio) | ❄️ **Obsoleta** — sustituida por FCM (D37), Twilio se elimina en Fase 7a |
| Fase 6 — Rediseño visual + landing dinámica (D35/D36) | ❄️ **Congelada** — landing y web funcionales; se abandona HTMX y smoke visual |
| Fase 7 — App móvil Android (React Native + Expo) | 📋 **Plan detallado** — 17 decisiones vía grilling, D37 ampliado, D39 actualiza el spike a dev build Android físico. Próximo paso: Spike dev build Android (bypass-silent) |

Detalle de checkboxes en `fases.md`.

---

## Próximos pasos

**Inmediato:**

1. **Spike dev build Android físico** (EAS Build cloud, sin Android Studio en PC): validar bypass-silent (DnD) + UI AlarmScreen con trigger local (sin FCM). Hardware Android disponible hoy. Ver Fase 7-Spike en `fases.md` (D39).
2. Opcional: **crear skill `ship-polished-ui`** (pospuesta de Sesión 6) — útil para Fase 7b.

**Fase 7a (backend):**
3. Eliminar `User`, auth JWT, teléfono, Twilio del backend.
4. Migración: nueva tabla `devices`, renombrar FKs en `BoutSubscription`/`AlertLog`.
5. `get_current_device` (header `X-Device-Id`) + endpoints `/api/devices`.
6. `GET /api/events` + `GET /api/events/{id}` JSON.
7. `FcmNotifier` con `firebase-admin` + configurar proyecto Firebase.
8. Refactor Poller: `Device.fcm_token` + timezone en vez de `User.phone`.
9. Tests + verificación completa (ruff/black/mypy/pytest).

**Fase 7b (app Android):**
10. Instalar Android Studio + emulador. Setup dev build en `mobile/`.
11. Native module Kotlin (bypass-silent alarm service).
12. Pantallas: Home, Eventos, EventDetail, Mis Alertas, Ajustes, AlarmScreen.

---

## Cómo levantar el backend en local (API-only, rama main)

```powershell
.\.venv\Scripts\Activate.ps1
# .env: DATABASE_URL=sqlite+aiosqlite:///./avisador.db
alembic upgrade head          # crea las tablas en avisador.db
uvicorn app.main:app --reload
```

- `http://localhost:8000/health` → `{"status":"ok"}`
- `http://localhost:8000/docs` → Swagger UI
- `/` → 404 (API-only, sin landing)

**La web (landing, admin, /app/*) solo existe en la rama `web`**: `git checkout web` y seguir
las mismas instrucciones de arriba.

---

## Notas de entorno

- **Python**: el `python` del PATH es 3.11; usar `py -3.12`. venv en `.venv`.
- **Redis local**: no es necesario para la web (la caché de atletas degrada a
  memoria); sí para idempotencia del Poller en producción.
- **Scheduler**: arranca con la app; en local sin Redis el poll loguea errores
  benignos si hay suscripciones activas. `SCHEDULER_ENABLED=false` para apagarlo.
- **Tip (PowerShell)**: usar `python -m pip` en vez de `pip`.
- **Hooks git**: activar una vez con `pwsh scripts/setup-hooks.ps1`.
- **Assets estáticos**: la web (rama `web`) tiene `src/app/web/static/` con CSS,
  fuentes e imágenes del hero. En main (API-only) no hay static — se eliminó con
  el split (D37). Para levantar la web: `git checkout web`.
- **tsparticles**: dependencia CDN de la landing (rama `web`). No aplica en main.
- **Skills de agente**: `.opencode/skills/` contiene:
  - Subset frontend de `addyosmani/agent-skills`: `frontend-ui-engineering`,
    `performance-optimization`, `code-review-and-quality` (+
    `references/accessibility-checklist.md` en frontend).
  - Subset productivity de `mattpocock/skills`: `grill-me` (user-invoked),
    `grilling` (model-invoked) — D38.
  - Si esta sesión no las ve activas, reinicia OpenCode (el config no es
    hot-reload).
- **Entorno app (nuevo)**: el proyecto Expo vivirá en `mobile/` (raíz del repo).
  Requiere Node 24.18+ (presente), `npx expo`, EAS CLI, Android Studio (para
  dev build y emulador). Aún no creado — se crea en Fase 7b.

---

## Comandos quick-start

```powershell
.\.venv\Scripts\Activate.ps1        # activar venv
alembic upgrade head                # aplicar migraciones (SQLite)
uvicorn app.main:app --reload        # servidor dev (API-only, sin web)
pytest -v                            # tests (64 verdes en main, 72 en rama web)
python scripts/probe_espn.py          # smoke ESPN en vivo
ruff check src tests                  # lint
black --check src tests scripts       # formato
mypy src/app                          # type check
python scripts/gen_memoria_index.py   # regenerar índice en AGENTS.md
```

