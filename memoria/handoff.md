# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

---

## Última sesión

**Fecha:** 2026-07-14 · **Sesión 8 — Spike bypass-silent (D39): build OK,
APK crashea en móvil**

**Contexto:** el owner consiguió un móvil Android físico hoy (ventana de
varias horas con hardware). Se decide cambiar el spike previsto en D37
(item #13, Expo Go + iPhone) por un **dev build Android físico** (D39) que
prueba el bypass-silent del audio (lo crítico del producto).

**Decisiones Esta sesión (D39):**
- El spike pasa de **Expo Go + iPhone** → **dev build Android físico** (EAS
  Build cloud, sin Android Studio en el PC).
- **Alcance recortado a solo sonido**: validar que `TYPE_ALARM` suena con el
  móvil en modo No Molestar. **Sin** full-screen intent, **sin**
  `expo-secure-store`, **sin** FCM, **sin** carátula MVP, **sin** Expo Router
  multi-pantalla. Razón: menos Kotlin a ciegas (sin emulador para debugear)
  = menos probabilidad de que la primera APK crashee. El full-screen intent,
  FCM y el resto entran en Fase 7b con Android Studio para iterar rápido.
- Solo se actualiza el item #13 de D37 — el resto intacto.

**Qué se hizo en esta sesión:**
- **D39 registrada** en `decisiones.md` (sustituye item #13 de D37).
- **Fase 7-Spike reescrita** en `fases.md` (solo sonido + bypass DnD).
- **Spike code en `mobile/`** (commit `532201d`, push a `origin/dev`):
  - Scaffold: `npx create-expo-app` (Expo SDK 57 + RN 0.86 + TypeScript).
  - `App.tsx`: 1 pantalla negra con 2 botones (Probar/Parar) + estado del
    servicio. Sin Expo Router, sin secure-store.
  - `npx expo prebuild --platform android` → `mobile/android/` generado.
  - Native module Kotlin en `mobile/android/app/src/main/java/com/despertarme/spike/alarm/`:
    - `AlarmModule.kt` — canal `despertarme.alarm` con `IMPORTANCE_HIGH` +
      `setBypassDnd(true)` + `setSound(null)` (streaming por `Ringtone`).
      Métodos `startAlarm()`/`stopAlarm()` expuestos a JS. Pide
      `ACCESS_NOTIFICATION_POLICY` si no lo tiene.
    - `AlarmService.kt` — foreground service tipo `mediaPlayback`.
      `RingtoneManager.TYPE_ALARM` (fallback `TYPE_RINGTONE`) en loop con
      `AudioAttributes(USAGE_ALARM)` + `PARTIAL_WAKE_LOCK` (10 min cap).
      Notification `CATEGORY_ALARM` + `setSilent(true)` (el sonido va por el
      `Ringtone`, no por la notification). Limpieza en `onDestroy`.
    - `AlarmPackage.kt` + registro en `MainApplication.kt`.
  - `AndroidManifest.xml`: permisos `ACCESS_NOTIFICATION_POLICY`,
    `FOREGROUND_SERVICE_MEDIA_PLAYBACK`, `POST_NOTIFICATIONS`, `WAKE_LOCK`,
    `VIBRATE` + `<service android:name=".alarm.AlarmService"
    foregroundServiceType="mediaPlayback"/>`.
  - `eas.json` perfil único `development` (APK internal, `assembleRelease`).
  - `mobile/README.md` con chuleta de build, permisos manuales en el móvil,
    y troubleshooting OEM (`adb logcat`, restricciones Xiaomi/Samsung).
  - TypeScript compila limpio (`tsc --noEmit`). Kotlin no se puede verificar
    sin compilar — primera build en la nube lo confirma.
- `.gitignore` de `mobile/` ajustado: `/android` ya no se ignora (commitea
  el Kotlin custom + manifest editado).
- **EAS login del owner** (cuenta `theni55`, `thenitrex1@gmail.com`).
- **`eas init`**: proyecto `@theni55/despertarme-spike` creado (ID
  `7e79b9e4-c187-4216-bbfd-ab2200b392d2`), linkeado en `mobile/app.json`
  (`extra.eas.projectId` + `owner`).
- **Build EAS #1 FALLIDA** (build `f3a519f8`, estado `ERRORED`):
  - Falló en la fase `INSTALL_DEPENDENCIES` (~1.5 s, antes de tocar
    Gradle/Kotlin). Error `npm ci`: `package.json and package-lock.json
    in sync` → `Missing: typescript@5.9.3 from lock file`.
  - **Causa raíz**: el agente (yo) metió `eas-cli` como devDependency del
    proyecto (`npm i --save-dev eas-cli`) tras el prebuild. `eas-cli` es
    CLI global, no dep de proyecto; ensució el árbol de deps y
    desincronizó el lock sin pensarlo.
  - **Fix aplicado**: `npm uninstall eas-cli` + `npm install` (regenera
    lock sincronizado con package.json limpio). Para futuras builds, usar
    `npx eas-cli` (descarga efímera) o `npm i -g eas-cli` (PC del owner),
    no meterlo en el proyecto.
- **Build EAS #1 FALLIDA** (build `f3a519f8`, estado `ERRORED`):
  - Falló en la fase `INSTALL_DEPENDENCIES` (~1.5 s, antes de tocar
    Gradle/Kotlin). Error `npm ci`: `package.json and package-lock.json
    in sync` → `Missing: typescript@5.9.3 from lock file`.
  - **Causa raíz**: el agente (yo) metió `eas-cli` como devDependency del
    proyecto (`npm i --save-dev eas-cli`) tras el prebuild. `eas-cli` es
    CLI global, no dep de proyecto; ensució el árbol de deps y
    desincronizó el lock sin pensarlo.
  - **Fix aplicado**: `npm uninstall eas-cli` + `npm install` (regenera
    lock sincronizado con package.json limpio). Para futuras builds, usar
    `npx eas-cli` (descarga efímera) o `npm i -g eas-cli` (PC del owner),
    no meterlo en el proyecto.
- **Build EAS #2 `FINISHED` ✅** (build `960ed029`, commit `81ca690`):
  - Cola ~6382 s (free tier saturado); compilación Gradle/Kotlin ~350 s
    (~6 min). El Kotlin a ciegas compiló limpio.
  - APK: `https://expo.dev/artifacts/eas/XUKdmgABRh-LmTGg5KxpaYjrD8y6CnBcImGM0Ygq-5c.apk`
    (válido hasta 28-jul-2026).
- **Prueba en móvil físico Android 14 → CRASH ❌**:
  - APK instalada, permiso de notificaciones concedido.
  - "Probar alarma" → la app **se cierra de golpe** sin mensaje de error
    capturado por JS. Crash de proceso nativo (el `AlarmService` arrancó
    y se cayó en seguida — la UI reached a mostrar "Service: stopped"
    antes de morir).
  - **Diagnóstico pendiente**: hace falta `adb logcat` para ver el stack
    trace exacto. El owner no ha hecho todavía el setup USB (platform-tools
    ~5MB + activar depuración USB + cable).
- **`expo doctor` aviso (no bloqueante, esperado)**: estamos en bare
  workflow (`mobile/android/` commiteado por el Kotlin custom). Ciertos
  campos de `app.json` no se sincronizan en cada build automáticamente.
  Si en Fase 7b se toca `app.json`, hay que correr
  `npx expo prebuild --platform android --clean` y re-commitear `android/`.

**Pendiente tras esta sesión:**
- **Login Expo** (gratis, https://expo.dev/signup): necesario para
  `eas build`. Pendiente del owner.
- **Build EAS** (~30-45 min cloud): `npx eas build --platform android --profile
  development` → URL de descarga APK.
- **Instalar APK + dar permisos manuales en el móvil** (notificaciones ON +
  "Anular el modo No Molestar" ON + volumen de alarma al máximo).
- **Probar**: móvil en DnD → "Probar alarma" → ¿suena `TYPE_ALARM`? → "Parar".
- Si no suena: `adb logcat` (platform-tools ~5MB standalone) para aislar
  qué eslabón falla (canal, foreground service, DnD, OEM).
- Crear skill `ship-polished-ui` (tarea pospuesta de la Sesión 6) — será
  útil durante Fase 7b para el diseño de la app.
- Arrancar Fase 7a (backend: device model + JSON endpoints + FCM notifier).

**Ramas:** `main` y `dev` están sincronizadas (ambas en `532201d`). La web
congelada vive en la rama `web` (snapshot del último commit de la era web,
`dcf62f8`). Para consultar la web: `git checkout web` y levantar con
`uvicorn app.main:app --reload`.

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
| Fase 7 — App móvil Android (React Native + Expo) | 🔶 **En curso** — Fase 7-Spike (solo sonido+bypass DnD): código en `dev`, build EAS #2 `FINISHED` ✅, APK instalada en móvil Android 14 → **CRASH al tocar "Probar alarma"**. Pendiente: `adb logcat` para diagnosticar el Kotlin. D37 + D39. |

Detalle de checkboxes en `fases.md`.

---

## Próximos pasos

**Inmediato:**

1. **Debug del crash en móvil**: el owner instala Android `platform-tools`
   (~5MB, sin Android Studio) + activa depuración USB + cable al PC. Yo
   ejecuto `adb logcat` filtrado para capturar el stack trace exacto del
   crash al tocar "Probar alarma".
2. Con el stack trace: **edit del Kotlin** (1-3 líneas casi seguro) +
   commit + push a `dev`.
3. **Relanzar Build EAS #3** (~6-15 min, deps cacheadas) → nueva URL APK.
4. Reinstalar APK en móvil + probar otra vez: "Probar alarma" →
   ¿suena `TYPE_ALARM` con DnD? → "Parar".
5. Actualizar memorias con el resultado del spike (D40 si hace falta).
6. Opcional: **crear skill `ship-polished-ui`** (pospuesta de Sesión 6) —
   útil para Fase 7b.

**Plan B (si no se puede hacer `adb logcat`)**: aplicar los 3 fixes
defensivos probables a ciegas (mover `startForeground` tras `play()`,
cambiar `setSmallIcon` a un drawable seguro, try/catch en
`playAlarmLoop` que devuelva error legible a JS) y relanzar build #3
sin diagnóstico previo. Más lento pero viable.

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

