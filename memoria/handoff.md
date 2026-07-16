# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

---

## Última sesión

**Fecha:** 2026-07-16 · **Sesión 15 — Scaffold Kotlin Compose (`mobile-kotlin/`) + Home/EventDetail navegables + smoke emulador OK. D43 + D44 registradas.**

**Contexto:** el owner confirmó en Sesión 14 el pivot a Kotlin nativo puro (sin Expo/RN) y pidió que esta sesión entregara visualmente lo que la web mostraba: Home con "Avísame" → pantalla de combates con nombres, fotos y datos de la API, y selector de minutos de aviso. El handoff Sesión 14 decía que este PC no tenía Android Studio, pero la verificación real reveló que **sí hay SDK Android portable + JDK 17 + AVD `pixel_6_api34`** (instalados en Sesiones 10-11) — solo falta el IDE Android Studio, que no es necesario para compilar con `gradlew`. D44 registrada para aclararlo a futuros continuadores.

**Hecho en esta sesión:**

1. `git mv mobile mobile-expo` (spike Expo preservado en WD, sin tocar histórico).
2. Scaffold `mobile-kotlin/` Compose **a mano** (sin wizard GUI, sin Node): `settings.gradle.kts`, `build.gradle.kts`, `gradle/libs.versions.toml` (version catalog), wrapper Gradle 8.11.1 (jar+scripts copiados del spike), `debug.keystore` generado con `keytool`. Stack: Compose BOM 2024.12 + Kotlin 2.0.21 + AGP 8.7.3 + Retrofit 2.11 (converter `kotlinx-serialization` **oficial** de Retrofit, no el de Jake Wharton que no resolvió) + Coil 2.7 + DataStore Preferences 1.1 + Navigation Compose 2.8 + Material3. minSdk 26 / targetSdk 34 / compileSdk 34. Paquete `com.despertarme.app`.
3. Código Kotlin Compose completo para 1+1 pantallas:
   - `DespertarMeApp.kt` (Application: canal `IMPORTANCE_HIGH` + `setBypassDnd` al crear — mismo del spike).
   - `MainActivity.kt` (single-activity Compose + NavHost `home → event/{eventId}`).
   - `ui/theme/` (tokens:`#E50914`, `#0A0A0A`, sans-serif — Inter sin embeber todavía).
   - `ui/screens/HomeScreen.kt`: hero `drawable-nodpi/hero.webp` (extraído de la rama `web`, D36/D42 — el póster oficial UFC 329) + veil degradado + botón rojo "Avísame" (navega a EventDetail del próximo evento) + botón secundario "Probar sonido" (arranca `AlarmService` portado del spike).
   - `ui/screens/EventDetailScreen.kt`: `LazyColumn` de combates, cada `BoutCard` con `matchNumber` + chip `cardSegment` (main/prelims) + `weightClass` + `periods`; columnas rojo/azul con `AsyncImage` (Coil) para `headshot_url` + `name` (placeholder si TBD); `FlowRow` de `FilterChip` para selector 5/10/15/30/60; botón "Avisarme" → `POST /api/subscriptions` con `X-Device-Id`; cambia a "Avisando ✓" tras suscripción; Snackbar "Alerta creada: X vs Y — N min".
   - `ui/viewmodel/EventDetailViewModel.kt` + `Factory` (inyección manual de `AppContainer` — `viewModel()` default no acepta constructor custom).
   - `data/remote/`: `DespertarApi` (Retrofit interface) + DTOs `@Serializable` (`EventCardOut`, `BoutOut`, `BoutAthleteOut`, `DeviceCreate`, `BoutSubscriptionCreate`...) + `DeviceIdInterceptor` (header `X-Device-Id`).
   - `data/DeviceStorage.kt`: DataStore Preferences, UUID v4 persistente.
   - `data/AppContainer.kt`: único `OkHttpClient` con `baseUrl=http://10.0.2.2:8000/`, registro best-effort en `ensureRegistered()` con token placeholder `no-fcm-yet-{uuid}` hasta el tramo FCM.
   - `alarm/AlarmService.kt` portado del spike a paquete `com.despertarme.app.alarm` (mismo `TYPE_ALARM` + `USAGE_ALARM` + `setBypassDnd` + `mediaPlayback` foreground validado Sesión 11).
4. `AndroidManifest.xml` con `usesCleartextTraffic=true` (necesario para HTTP en API 28+ — sin esto la app traga IOException silenciosamente) + permisos completos (FOREGROUND_SERVICE_MEDIA_PLAYBACK, USE_EXACT_ALARM, USE_FULL_SCREEN_INTENT, RECEIVE_BOOT_COMPLETED, los del spike).
5. **3 iteraciones de build** hasta `BUILD SUCCESSFUL` — 3 fixes aplicados:
   - `signingConfigs.getByName("debug")` en lugar de `create("debug")` (AGP ya crea uno por defecto).
   - `com.squareup.retrofit2:converter-kotlinx-serialization` (oficial Retrofit 2.11) en lugar de `com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter` (este no exponía el import `retrofit2.converter.kotlinx.serialization.asConverterFactory`).
   - `androidx.compose.foundation.layout.FlowRow` + `@OptIn(ExperimentalLayoutApi::class)` (no está en `androidx.compose.material3`).
   - `Image(painterResource(R.drawable.hero), ...)` en HomeScreen en lugar de `AsyncImage(model: Painter?, ...)` (Coil rechaza Painter como model: `IllegalArgumentException: Unsupported type: Painter`).
6. **Smoke emulador** `pixel_6_api34` arrancado + `adb reverse tcp:8000 tcp:8000` (puente emulador→host, complementa 10.0.2.2 AOSP nativo). APK 21.9 MB instalado. App arranca sin FATAL, Activity visible.
7. **Backend SQLite levantado** con `cwd` en raíz del repo (no `src/` — si no, pydantic-settings no encuentra `.env` y cae a defaults Postgres asyncpg rechazado por no haber Docker; error visible en `uvicorn.err`). `alembic upgrade head` aplicado.
8. **Smoke end-to-end verificado**:
   - `GET /health` → 200 `{"status":"ok","env":"development"}`.
   - `POST /api/devices` (curl simulación app) → 201 Created.
   - `POST /api/subscriptions` (curl) → 201 Created con suscripción `edf42792-dc44-41fc-a04b-e9c2f839741c` (Du Plessis vs Usman, lead 15 min).
   - `GET /api/events/600059599` → 200 con 12 combates reales y nombres de peleadores (Ezra Elliott vs Damien Anderson, etc.).
   - `GET /api/subscriptions` → 200 devuelve la sub nueva.
   - **Tráfico real de la app en `uvicorn.out`**: desde puerto 55980 (app) → `POST /api/devices` + `GET /api/events` (registro + LaunchedEffect Home). Desde puerto 56063 (tras `adb tap 540 2150`) → `GET /api/events/600059599` (navegación Home→EventDetail exitosa, card cargada en la app).
   - **SQLite verificado**: device `e57d6077-7ef4-4e68-bb99-8d9d8a2ae174` registrado por la app (platform=android, locale=es-ES). La app ya persistió su UUID en DataStore.

**Decisiones nuevas:** D43 (pivot a Kotlin nativo + Compose, supersede D37) y D44 (nota técnica entorno del owner: SDK portable sin IDE Android Studio, compilar vía `gradlew`).

**Pendiente de la próxima sesión** (Paso 2 + 3 de Fase 7b, ver `fases.md`):
1. **`AlarmScheduler`** (`AlarmManager.setAlarmClock()` a `estimated_start_at − lead_minutes`) + `AlarmReceiver` + verify-then-ring (fetch `GET /api/events/{id}` al disparar → sonar / reprogramar / silenciar) + `AlarmActivity` full-screen + `BootReceiver` (re-programar tras reinicio). Doze validation con `dumpsys deviceidle force-idle`. Esto es lo que falta para que el botón "Avisarme" realmente programe la alarma local que sonará a la hora estimada del combate — hoy solo persiste la suscripción en BD.
2. Pantallas restantes: Mis Alertas, Eventos lista, Ajustes, AlarmScreen dedicado.
3. Tramo FCM: Firebase project + `google-services.json` + Redis (`docker compose up -d` para desbloquear poller).
4. Validación en hardware físico + deploy Railway.

**⚠️ Nota operativa para futuras sesiones:** env vars `JAVA_HOME` (JDK 17 Temurin portable) + `ANDROID_HOME` + `PATH` (emulator + platform-tools + cmdline-tools) ya están fijados en perfil User. Para compilar `mobile-kotlin/`:
```powershell
$env:JAVA_HOME = "C:\Users\pacor\AppData\Local\jdk-17\jdk-17.0.19+10"
$env:Path = "$env:JAVA_HOME\bin;$env:LOCALAPPDATA\Android\Sdk\platform-tools;$env:LOCALAPPDATA\Android\Sdk\emulator;$env:Path"
& "X:\Project IA\DespertarME\mobile-kotlin\gradlew.bat" -p "X:\Project IA\DespertarME\mobile-kotlin" assembleDebug --no-daemon --console=plain
```
Para levantar el backend:
```powershell
.\.venv\Scripts\Activate.ps1   # ⚠️ cwd debe ser raíz del repo, no src/
# .env: DATABASE_URL=sqlite+aiosqlite:///./avisador.db
alembic upgrade head
uvicorn app.main:app --reload   # o --host 0.0.0.0 para emulador
```
Para el emulador:
```powershell
emulator -avd pixel_6_api34
adb reverse tcp:8000 tcp:8000   # puente emulador→host
adb install -r mobile-kotlin\app\build\outputs\apk\debug\app-debug.apk
adb shell am start -n com.despertarme.app/.MainActivity
```

---

## Sesión 14 (anterior)

**Fecha:** 2026-07-16 · **Sesión 14 — Decisión: pivot a Kotlin nativo puro (sin Expo/RN) para la app Android. Plan de ejecución consolidado.**

**Contexto:** el owner preguntó si, teniendo Android Studio, se podía quitar Expo para simplificar el desarrollo. Análisis: la funcionalidad crítica del MVP (AlarmScheduler, AlarmService, AlarmActivity, bypass DnD, FCM) es Kotlin sí o sí — Expo solo cubría la capa de pantallas a cambio de mantener dos runtimes (JS + nativo), el bridge, Metro, Node y EAS (que ya dio problemas: build ERRORED por lock, colas ~2h). **Decisión del owner: quitar Expo e ir a Kotlin nativo + Jetpack Compose.**

⚠️ **D43 registrada en Sesión 15** (no en 14). §7b/7c reescritas en Sesión 15 con el stack Kotlin real.

**Hallazgo de entorno (verificado Sesión 15):** el handoff Sesión 14 decía que este PC NO tenía Android Studio, ni SDK, ni adb, ni AVD; Java 1.8. Era **incorrecto** — en Sesiones 10-11 el SDK Android portable + JDK 17 + AVD `pixel_6_api34` ya estaban instalados (sin IDE Android Studio GUI, pero suficientes para compilar/arrancar emulador vía CLI). Ver D44 para el detalle exacto. Hipervisor activo ✅. Sin Android Studio IDE → `winget install Google.AndroidStudio` si se quiere el wizard GUI, pero no es necesario para compilar.

---

## Próximos pasos (plan aprobado Sesión 14, ejecutado parcialmente Sesión 15)

### Paso 1 — Scaffold + Home/EventDetail navegables ✅ (Sesión 15)
- Renombrado `mobile/` → `mobile-expo/` (preserva spike).
- Scaffold Kotlin Compose compilando en `mobile-kotlin/` con `gradlew assembleDebug` (sin IDE).
- Backend SQLite levantado, emulador arrancado, APK instalado, smoke end-to-end OK (registro + list events + navigation + event detail fetch desde la app).
- D43 + D44 registradas en `decisiones.md`. §7b/7c reescritas en `fases.md`.

### Paso 2 — `AlarmScheduler` + verify-then-ring (próxima sesión, camino crítico D40)
- `AlarmManager.setAlarmClock()` a `estimated_start_at − lead_minutes` + `AlarmReceiver` + verify-then-ring (fetch `GET /api/events/{id}` al disparar → sonar/reprogramar/silenciar). Refactor `AlarmService`: sonido custom `res/raw/alarm.ogg` + `AlarmActivity` full-screen. `BootReceiver` para re-programar tras reboot.
- Doze: `adb shell dumpsys deviceidle force-idle` → `setAlarmClock` despierta puntualmente.

### Paso 3 — Pantallas Compose restantes (~1-2 sesiones)
- Eventos lista, Mis Alertas, Ajustes (con test-alarm real), AlarmScreen modal.

### Paso 4 — Tramo FCM (aquí entran las deps externas)
- Firebase (manual owner, ~30 min): proyecto + service account JSON → `FCM_CREDENTIALS_JSON` (backend) + `google-services.json` → `mobile-kotlin/app/`.
- Redis (`docker compose up -d`): desbloquea el poller (idempotencia D16).
- Cliente FCM nativo (`firebase-messaging`): `update` → reprogramar alarma; `started`/`cancelled` → notificación informativa.

### Paso 5 — Validación final + deploy (Fase 7c)
- Móvil físico (bypass DnD real + quirks OEM) → Railway (PG + Redis + `FCM_CREDENTIALS_JSON`) → `./gradlew assembleRelease` local → smoke end-to-end.

### Paso 6 — Deuda de la review Sesión 13 (oportunista, no bloquea)
- `message_type` en el UNIQUE de `alert_log` · UUID v4 estricto en `DeviceCreate` · nits listados en Sesión 13.

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
| Fase 5 — VoiceNotifier real (Twilio) | ❄️ **Obsoleta** — sustituida por FCM (D37/D40) |
| Fase 6 — Rediseño visual + landing dinámica | ❄️ **Congelada** — rama `web` |
| Fase 7 — App móvil | 🔶 **En curso** — Spike ✅, Fase 7a (backend Device/FCM) ✅ + review con 4 fixes ✅. **Sesión 15: pivot a Kotlin nativo puro (D43) ejecutado. Scaffold `mobile-kotlin/` Compose + Home/EventDetail navegables + smoke emulador OK. Próximo: `AlarmScheduler` D40 + pantallas restantes.** |

Detalle de checkboxes en `fases.md`.

---

## Ramas

- `dev` (activa): backend API-only + `mobile-expo/` spike (preservado) + `mobile-kotlin/` Compose nuevo + memoria viva.
- `main`: sincronizada con `dev` hasta Fase MVP-launch (el pivot 7a aún no está en main).
- `web` (congelada en `dcf62f8`): landing, admin web, `/app/*`. `git checkout web` para consultarla.

---

## Cómo levantar el backend en local

```powershell
.\.venv\Scripts\Activate.ps1
# ⚠️ cwd debe ser raíz del repo, no src/ (si no, .env no se carga y cae a Postgres asyncpg)
# .env: DATABASE_URL=sqlite+aiosqlite:///./avisador.db
alembic upgrade head
uvicorn app.main:app --reload         # usar --host 0.0.0.0 para emulador
```

- `http://localhost:8000/health` → `{"status":"ok"}`
- `http://localhost:8000/docs` → Swagger UI (9 endpoints: devices, events, subscriptions, alerts, health)

**La web solo existe en la rama `web`.**

---

## Cómo compilar y arrancar la app Android (en este PC)

```powershell
# Env vars (ya en perfil User — explícito para SESIONES posteriores o si reinicia):
$env:JAVA_HOME = "C:\Users\pacor\AppData\Local\jdk-17\jdk-17.0.19+10"
$env:Path = "$env:JAVA_HOME\bin;$env:LOCALAPPDATA\Android\Sdk\platform-tools;$env:LOCALAPPDATA\Android\Sdk\emulator;$env:Path"

# Compilar
& "X:\Project IA\DespertarME\mobile-kotlin\gradlew.bat" -p "X:\Project IA\DespertarME\mobile-kotlin" assembleDebug --no-daemon --console=plain

# Emulador + puente + instalar + arrancar
emulator -avd pixel_6_api34 -no-snapshot-save -no-boot-anim
# (en otra terminal) esperar boot:
adb wait-for-device & adb shell 'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 1; done; exit' ; echo ready
adb reverse tcp:8000 tcp:8000
adb install -r mobile-kotlin\app\build\outputs\apk\debug\app-debug.apk
adb shell pm grant com.despertarme.app android.permission.POST_NOTIFICATIONS
adb shell am start -n com.despertarme.app/.MainActivity

# Diagnóstico
adb logcat -d *:E | findstr /C:"FATAL" /C:"AndroidRuntime"
adb logcat -d | findstr /C:"DespertarMe"
```

---

## Comandos quick-start

```powershell
.\.venv\Scripts\Activate.ps1            # activar venv
alembic upgrade head                    # aplicar migraciones (SQLite dev)
uvicorn app.main:app --reload            # servidor dev (API-only)
pytest -v                                # tests (80 verdes en dev)
python scripts/probe_espn.py              # smoke ESPN en vivo
ruff check src tests                      # lint
black --check src tests scripts           # formato
mypy src/app                              # type check
python scripts/gen_memoria_index.py       # regenerar índice en AGENTS.md
```