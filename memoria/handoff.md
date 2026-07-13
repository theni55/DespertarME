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
  `bitacora.md` (entrada de la sesión).
- **En curso**: sesión de grilling para refinar el plan de Fase 7
  (decisiones de implementación aún pendientes).

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
| Fase 5 — VoiceNotifier real (Twilio) | **Completada** ✅ (pendiente cuenta Twilio del owner) |
| Fase 6 — Rediseño visual + landing dinámica (D35/D36) | ❄️ **Congelada** — landing y web funcionales; se abandona HTMX y smoke visual |
| Fase 7 — App móvil Android (React Native + Expo) | 🔶 **En planificación** — grilling en curso para cerrar decisiones de implementación |

Detalle de checkboxes en `fases.md`.

---

## Próximos pasos

**Inmediato (cerrar planificación Fase 7):**

1. **Completar grilling**: resolver las decisiones pendientes
   (`decisiones.md` → "Decisiones pendientes (Fase 7)") una a una.
2. **Crear skill `ship-polished-ui`** (tarea pospuesta de Sesión 6) —
   contenido detallado en el handoff anterior.

**Después del grilling (arrancar Fase 7a):**

3. Migración Alembic: `Device` + `device_id` en `BoutSubscription`/`AlertLog`.
4. Endpoints `/api/devices`, `GET /api/events`, `GET /api/events/{id}` JSON.
5. `FcmNotifier` con `firebase-admin`.
6. Refactor Poller: `Device.fcm_token` + timezone en vez de `User.phone`.
7. Admin web refactorizado a devices.
8. Tests + verificación completa (ruff/black/mypy/pytest).

**Después de Fase 7a (arrancar Fase 7b):**

9. Setup proyecto Expo + Native module Android (alarma).
10. Spike: validar FCM → alarma bypass DnD en dispositivo físico real.
11. Pantallas: Home, Eventos, EventDetail, Mis Alertas, Ajustes, AlarmScreen.
12. Build EAS → APK interno → prueba con el owner.

---

---

## Cómo levantar la web en local

```powershell
.\.venv\Scripts\Activate.ps1
# .env: DATABASE_URL=sqlite+aiosqlite:///./avisador.db (append tras copiar .env.example)
alembic upgrade head          # crea las tablas en avisador.db
uvicorn app.main:app --reload
```

**Landing pública (D35/D36, pantalla única):**
- `http://localhost:8000/` → landing de pantalla única (imagen del cartel de
  fondo + partículas + botón "Avísame"). Ya no redirige a `/app`; se muestra
  siempre, incluso con sesión activa.

**Usuario (vista funcional):**
- `http://localhost:8000/app/login` / `/app/register` → auth de usuario
- `http://localhost:8000/app` → dashboard (requiere cookie de sesión)
- `http://localhost:8000/app/events/{event_id}` → tarjeta con fotos y nombres + crear alerta

**Admin:**
- `http://localhost:8000/admin/login` (seed: `python scripts/seed_admin.py`)
- `http://localhost:8000/admin/users/{id}` → detalle de usuario
- `http://localhost:8000/docs` → Swagger UI

---

## Notas de entorno

- **Python**: el `python` del PATH es 3.11; usar `py -3.12`. venv en `.venv`.
- **Redis local**: no es necesario para la web (la caché de atletas degrada a
  memoria); sí para idempotencia del Poller en producción.
- **Scheduler**: arranca con la app; en local sin Redis el poll loguea errores
  benignos si hay suscripciones activas. `SCHEDULER_ENABLED=false` para apagarlo.
- **Tip (PowerShell)**: usar `python -m pip` en vez de `pip`.
- **Hooks git**: activar una vez con `pwsh scripts/setup-hooks.ps1`.
- **Assets estáticos**: `src/app/web/static/{css,fonts,img}/`, montados en
  `/static` vía `StaticFiles`. Sin build step — CSS puro, sin bundler ni
  `package.json`. `fonts/inter-var-latin.woff2` es la tipografía Inter
  Variable auto-hospedada (D35); `img/hero.webp`+`hero.jpg` son el póster de
  fondo de la landing (regenerar con `ffmpeg` si cambia el evento destacado).
- **tsparticles**: única dependencia por CDN del proyecto (versión pinneada
  `2.12.0` en jsdelivr) — rompe puntualmente el principio "sin CDN" de D35
  (que solo cubría fuentes), aceptado como progressive enhancement (D36).
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
uvicorn app.main:app --reload        # servidor dev (API + web + scheduler)
pytest -v                            # tests (72/72 verdes)
python scripts/probe_espn.py          # smoke ESPN en vivo
ruff check src tests                  # lint
black --check src tests scripts       # formato
mypy src/app                          # type check
python scripts/gen_memoria_index.py   # regenerar índice en AGENTS.md
```

