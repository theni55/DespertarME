# Plan MVP visual + funcional — App Android (para Fable 5)

> Plan por fases con checkboxes para completar un MVP visual y funcional de la app Android (Kotlin/Compose) en `mobile-kotlin/`, pensado para cargarlo en Fable 5 vía `/goal`.

## 0. Contexto que hay que conocer antes de tocar código

- Repo: `theni55/DespertarME`, rama de trabajo **`dev`** (⚠️ `main` no tiene aún el pivot a `mobile-kotlin/`, no mergear ahí sin confirmar).
- Backend ya existe y funciona: FastAPI + SQLAlchemy async + Alembic en `src/app/`. 9 endpoints REST documentados en `/docs`. No hay que rehacerlo, solo consumirlo y, si acaso, tocar 2 endpoints puntuales del cliente Kotlin que faltan por invocar (`DELETE /api/subscriptions/{id}`, `GET /api/alerts`).
- App Android ya tiene scaffold funcionando en `mobile-kotlin/` (Compose, package `com.despertarme.app`): `HomeScreen`, `EventDetailScreen` con tarjetas de combate, tema oscuro con rojo `#E50914`/fondo `#0A0A0A` ya definidos en `ui/theme/Color.kt`, `AlarmService` que hace sonar `TYPE_ALARM` con bypass de No Molestar (ya validado en Sesión 11 con un dispositivo físico, en **otro** PC del proyecto).
- Lee `memoria/handoff.md`, `memoria/fases.md` (Fase 7b) y `memoria/decisiones.md` (D37, D40–D44) antes de empezar — contienen decisiones ya cerradas que no hay que reabrir sin justificar una nueva decisión (`D45`, etc.).
- Las 3 capturas `memoria/assets/imagen_referencia_1/2/3.jpeg` son la referencia de estilo (app Winamax): fondo oscuro, tarjetas con foto a toda anchura, tipografía grande en negrita, acento rojo, barra de navegación inferior con iconos, buscador simple. Úsalas como inspiración de composición de tarjeta y navegación, no copiar branding/apuestas.
- **Alcance de la alarma en este documento, en dos fases separadas** (decisión del owner):
  - **Fase E (este documento, automatizable 100%):** alarma de un solo disparo programada al suscribirse, sin reprogramación en tiempo real.
  - **Fase G (más adelante, bloqueada por un paso manual):** reprogramación en tiempo real vía FCM — es el objetivo de producto "real" documentado en `handoff.md`, pero requiere que el owner cree un proyecto Firebase a mano. Se documenta aquí para que Fable 5 la retome en cuanto el prerrequisito esté listo, no para bloquear el resto del plan.

---

## Fase A — Entorno de desarrollo Android en esta máquina

**Objetivo:** poder compilar y ejecutar `mobile-kotlin/` en un emulador desde esta máquina Windows (`javier.romero`), que hoy no tiene nada instalado.

- [x] Verificar virtualización real antes de instalar nada: hipervisor activo confirmado (`hvservice` + `vmcompute` corriendo, WSL2 con Ubuntu). El `VirtualizationFirmwareEnabled=False` era el falso negativo clásico con Hyper-V on. `emulator -accel-check` → "WHPX(10.0.26100) is installed and usable". No se instaló HAXM (correcto).
- [x] Instalar **Android Studio** completo — `winget install Google.AndroidStudio` → versión 2026.1.2.10 en `C:\Program Files\Android\Android Studio` (jbr = OpenJDK 21.0.10).
- [x] SDK instalado vía **cmdline-tools + sdkmanager** (sin wizard GUI, automatizable): `platform-tools 37.0.0`, `platforms;android-34`, `build-tools;34.0.0`, `emulator 36.6.11`, `system-images;android-34;google_apis;x86_64`, `cmdline-tools (latest)`. Licencias aceptadas. SDK en `%LOCALAPPDATA%\Android\Sdk`.
- [x] Crear un **AVD**: `pixel_6_api34` (Pixel 6, API 34, Google APIs x86_64) creado con `avdmanager`.
- [x] Configurar JDK: `JAVA_HOME` (Machine) ya apuntaba al **JDK 21 de Microsoft** (`C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot`) — ≥17, válido para el proyecto; `gradlew.bat` lo usa. (El handoff previo decía que no estaba en `JAVA_HOME` — ya no es el caso.)
- [x] Variables de entorno de usuario: `ANDROID_HOME` fijada + `platform-tools`, `emulator` y `cmdline-tools\latest\bin` añadidos al `PATH` de usuario.
- [x] Proyecto compilando desde terminal con `gradlew` (Android Studio queda instalado para cuando el owner quiera el IDE; File → Open sigue pendiente de primer uso GUI). `local.properties` creado con `sdk.dir` (gitignored) y `app/debug.keystore` regenerado con `keytool` (gitignored — cada máquina genera el suyo).
- [x] **Criterio de aceptación:** `gradlew assembleDebug` → **BUILD SUCCESSFUL** (1m 10s) y AVD arrancado con "Windows Hypervisor Platform accelerator is operational", `sys.boot_completed=1`, Android 14. ✅ (2026-07-17)

## Fase B — Backend local operativo

**Objetivo:** tener la API FastAPI corriendo en local con datos reales de ESPN, accesible desde el emulador.

- [x] Setup ya existía en esta máquina (venv Python 3.12.10 + `.env` con `DATABASE_URL=sqlite+aiosqlite:///./avisador.db` + paquete `avisador==0.1.0` instalado). Verificado, no rehecho.
- [x] `alembic upgrade head` aplicado (head `f7a0001_devices`) y `uvicorn app.main:app --host 0.0.0.0` con cwd en la raíz del repo.
- [x] Smoke test: `GET /health` → `{"status":"ok"}`.
- [x] ⚠️ **Quirk máquina corporativa (2026-07-17):** el proxy TLS de Inditex (CA self-signed en la cadena) rompía las llamadas a ESPN con `CERTIFICATE_VERIFY_FAILED`. Fix local sin tocar código del repo: `pip install truststore` + `sitecustomize.py` en `.venv/Lib/site-packages/` con `truststore.inject_into_ssl()` (usa el almacén de certificados de Windows). El venv es gitignored — si se recrea, hay que repetirlo.
- [x] `adb reverse tcp:8000 tcp:8000` aplicado en el smoke del emulador.
- [x] **Criterio de aceptación:** `POST /api/devices` → 201; `GET /api/events/600059599` → 12 combates con nombres reales (Anna Melisano vs Dione Barbosa, etc.). ✅ (2026-07-17)

## Fase C — Sistema visual (aplicar la referencia de estilo)

**Objetivo:** que Home y EventDetail se vean con la densidad/impacto visual de las capturas de referencia (tarjetas con foto a toda anchura, tipografía bold, acento rojo, navegación inferior), sin romper lo que ya funciona.

Estado actual: tema ya define `UfcRed #E50914`, `BackgroundDark #0A0A0A`, tarjetas con `SurfaceDark`, columnas rojo/azul con avatar circular + iniciales de fallback. Esto es un buen punto de partida — **no reescribir desde cero**, evolucionar:

- [x] **Bottom navigation bar** (Home / Eventos / Mis Alertas / Ajustes) con `NavigationBar` Material3 + iconos Material Icons Extended, integrada en `MainActivity.kt` (`AppGraph`) envolviendo el `NavHost` con `Scaffold`. Seleccionado en rojo `UfcRed`, indicador con alpha.
- [x] **HomeScreen**: sin cambios de hero (decisión cerrada del owner Sesión 15: "se quedará así la imagen"). Botón "Probar sonido" convertido en toggle "Probar/Parar sonido" (ver nota AlarmService abajo).
- [x] **BoutCard (EventDetailScreen)** pulido:
  - Badge de `cardSegment` con color distintivo: `main*` en rojo `UfcRed` traslúcido, prelims en azul `BlueCorner` traslúcido (antes gris plano).
  - Borde rojo + chip "PRÓXIMO" en la tarjeta del primer combate de la lista (el próximo en suceder — el backend lista en orden cronológico), equivalente al borde destacado de Winamax.
  - (Foto grande "media tarjeta" tipo Winamax: no aplicado — requiere confirmación del owner, los headshots de ESPN son cuadrados pequeños y escalar avatar 80dp ya cubre el MVP.)
- [x] **Pantalla "Eventos"**: tarjeta-lista con franja degradada roja + icono guante (sustituto de la imagen: ESPN aún no sirve `image_url`, D42) + nombre bold + fecha con punto rojo.
- [x] Tipografía: **evaluada y diferida** — embeber Inter en `res/font/` requiere añadir binarios TTF al repo y el beneficio visual con los pesos bold del sistema es marginal en esta fase. Retomar si el owner quiere identidad tipográfica exacta con la web.
- [x] **Criterio de aceptación:** smoke visual manual en emulador (2026-07-17) — Home, Eventos, EventDetail, Mis Alertas y Ajustes con look & feel coherente (fondo `#0A0A0A`, tarjetas `#1A1A1A`, bold, acento `#E50914`), navegables desde la barra inferior. Capturas verificadas durante la sesión.

## Fase D — Pantallas y navegación completas

**Objetivo:** cerrar las pantallas que hoy faltan (documentadas como pendientes en `fases.md` Fase 7b Paso 3), reutilizando los endpoints backend ya existentes.

- [x] **Cliente API**: añadidos a `DespertarApi.kt` `@DELETE("/api/subscriptions/{id}")` y `@GET("/api/alerts")` con `@Query("limit")`; DTO `AlertLogOut` en `Models.kt` mapeando `app/api/schemas.py::AlertLogOut` completo.
- [x] **Pantalla "Eventos"** (`ui/screens/EventListScreen.kt` + `EventListViewModel`): `GET /api/events`, tarjetas con nombre + fecha, tap → `event/{id}` (reutiliza `EventDetailScreen`).
- [x] **Pantalla "Mis Alertas"** (`ui/screens/SubscriptionsScreen.kt` + `SubscriptionsViewModel`): `GET /api/subscriptions` + cancelar (`DELETE`, con snackbar) + historial `GET /api/alerts`. Los nombres de peleadores se resuelven con un fetch por evento único (el backend solo devuelve ids en la sub); fallback "Combate #N".
- [x] **Pantalla "Ajustes"** (`ui/screens/SettingsScreen.kt`): device_id (monospace) + timezone + toggle "Probar/Parar alarma" + estado de permisos (notificaciones vía `checkSelfPermission`, alarmas exactas vía `canScheduleExactAlarms`).
- [x] `MainActivity.kt`/`AppGraph` con las 4 rutas top-level + `event/{eventId}` + `NavigationBar` (patrón `popUpTo(findStartDestination) { saveState } + launchSingleTop + restoreState`).
- [x] **Criterio de aceptación** (verificado en emulador 2026-07-17): 4 pantallas navegables sin crashes (logcat sin FATAL); suscripción desde EventDetail (`POST` 201) aparece en Mis Alertas con nombres reales; cancelar (`DELETE` 204) la borra con snackbar "Alerta cancelada"; historial se lista (vacío, esperado — ninguna alerta ha sonado).

## Fase E — Alarma funcional v1 (sin FCM, un solo disparo) ✅ COMPLETADA + REVISADA (Sesión 18, D45)

**Objetivo:** que el botón "Avisarme" programe una alarma real del sistema que suene a la hora estimada. **Modelo original revisado (D45):** la alarma ya NO se pre-programa al suscribirse con `bout.date` de ESPN. En su lugar, el backend envía push FCM `update` cuando el combate previo transiciona a `in` o `post` (no en `pre`). La app programa la alarma al recibir el push, con cushion siempre +1 min. Ring-once via flag `fired=true`. Ver `memoria/decisiones.md` D45 para el detalle completo.

> Nota (Sesión 18): `AlarmScheduler`, `AlarmReceiver`, `AlarmActivity`, `BootReceiver` y `DespertarMeFirebaseService.handleUpdate()` ya implementados con el modelo D45. `LEAD_OPTIONS = [5, 10, 15, 30]` (60 min eliminado).**

- [x] **`AlarmScheduler`**: `AlarmManager.setAlarmClock()`. Cancelar/reprogramar. Persistencia en DataStore via `PendingAlarmStorage`.
- [x] **`AlarmReceiver`**: al disparar → arranca `AlarmService` + `AlarmActivity`. Marca `fired=true` (ring-once D45).
- [x] **`AlarmActivity`** (pantalla full-screen sobre lockscreen): Compose, `setShowWhenLocked`, `setTurnScreenOn`, botón "Descartar" → `ACTION_STOP`.
- [x] **`BootReceiver`**: re-programa tras reinicio leyendo `PendingAlarmStorage.all()`.
- [x] `EventDetailViewModel.subscribe()` → tras `POST /api/subscriptions` exitoso, persiste `PendingAlarm(triggerAtMillis=0L, fired=false)` como centinela — NO programa alarma.
- [x] `DespertarMeFirebaseService.handleUpdate()` → lógica D45: fired-check, lead>=30 special case, cushion siempre +1 min.
- [x] `DespertarMeFirebaseService.cancelAlarmAndNotify()` → marca `fired=true` antes de cancelar.
- [ ] **Validación Doze** y **smoke E2E con evento real** — pendiente de Docker Desktop (Redis) para el poller del backend.
- [x] ⚠️ **Nota honesta para el owner (actualizada):** el modelo D45 resuelve el problema original. Sin FCM no habría reprogramación, pero con FCM + el guard D45 (no pushear en `pre`), la alarma solo se programa cuando hay datos reales del combate previo. Sin Redis/Docker el poller no corre → no se puede validar E2E aún. Queda como prerequisito operativo para la próxima sesión.

## Fase F — Validación end-to-end del MVP

- [ ] Backend local + emulador arrancados según Fases A/B.
- [ ] Recorrido completo manual: Home → Eventos → EventDetail → suscribirse → Mis Alertas muestra la suscripción → Ajustes → Probar alarma suena con bypass DnD → esperar disparo real de una alarma de prueba con lead corto → AlarmActivity aparece → Descartar detiene el sonido.
- [ ] Revisar `logcat` sin `FATAL`/`AndroidRuntime` durante todo el recorrido.
- [ ] Capturar pantallas del resultado final para comparar visualmente contra las 3 referencias de Winamax en `memoria/assets/` (composición de tarjeta, contraste, navegación).
- [ ] **Definition of Done del MVP visual+funcional:** 4 pantallas navegables con estilo coherente, suscripción real contra el backend, alarma de un solo disparo sonando con bypass de silencio en el emulador, sin crashes.

## Fase G — Reprogramación en tiempo real vía FCM ✅ COMPLETADA + E2E VERIFICADA EN EMULADOR (Sesión 18, D45)

**Prerrequisito manual del owner completado** (Sesión 18): Firebase project `despertarme-73d00` con Cloud Messaging habilitado, service account JSON + `google-services.json` generados y pegados en el repo. Código implementado: ver `memoria/decisiones.md` D45 para el modelo completo.

**Smoke E2E en emulador verificado (17-18 jul 2026):**
- Firebase token real obtenido por la app en emulador `pixel_6_api34` (Google APIs system image) — confirmado que FCM funciona sin Google Play, solo con Play Services.
- `POST /api/devices/me/test-alarm` → push `fire` → AlarmService arranca + AlarmActivity aparece + TYPE_ALARM suena. Pipeline básico OK.
- Endpoint debug temporal `POST /api/debug/simulate-transition?bout_id=401889642&estimated_start_in_minutes=10` (borrado tras el test) → backend mandó push `update` real con epoch millis.
- App recibió → `handleUpdate()` calculó cushion correctly → `AlarmScheduler.schedule(trigger=now+6min)` → `setAlarmClock` en `dumpsys alarm`.
- A los 6:02 min exactos: `AlarmReceiver` disparó → `fired=true` marcado → `AlarmActivity` opened on lockscreen + `AlarmService` (TYPE_ALARM sonando) + `AudioTrack frames delivered`.
- Alarma silenciada con `adb shell am force-stop` (botón "Descartar" de AlarmActivity también lo detiene).
- Endpoint debug + su gate `if app_env=="development"` en `main.py` borrados tras el test. `pytest` 80/80 ✅.

**Pendiente de validación con evento real:**
- UFC Fight Night: Du Plessis vs Usman el 18 de julio. Prelims a las 23:00 CEST (21:00 UTC), main card a las 02:00 CEST del 19 (00:00 UTC).
- Suscribirse desde la app a un combate actual (no los bout_id obsoletos de pruebas previas — ESPN los reasigna).
- Dejar el backend corriendo con Redis (Docker Desktop) y esperar a que el poller detecte `pre→in` o `in→post` reales de ESPN → push FCM `update` automático → alarma programa → suena a la hora calculada.

### Prerrequisito manual del owner (~30 min, fuera del alcance de cualquier agente)
1. Crear proyecto `despertarme` en [console.firebase.google.com](https://console.firebase.google.com).
2. Habilitar Cloud Messaging (Build → Cloud Messaging).
3. Generar **service account key** (Project settings → Service accounts → Generate new private key) → guardar el JSON.
4. Registrar app Android con package `com.despertarme.app` → descargar `google-services.json`.

### Una vez el owner entregue las credenciales (automatizable)
- [ ] Backend: `FCM_CREDENTIALS_JSON` en `.env` (el código de `notifiers/fcm.py` ya está listo desde Fase 7a, solo gatea por env-var).
- [ ] `google-services.json` → `mobile-kotlin/app/`.
- [ ] Plugin `com.google.gms.google-services` + dependencia `firebase-messaging` en `build.gradle.kts`/`libs.versions.toml`.
- [ ] `FirebaseMessagingService` en Kotlin: payload data-only `type=update|started|cancelled` → `update` reprograma `AlarmScheduler` con el nuevo `estimated_start_at`; `started`/`cancelled` muestran notificación informativa.
- [ ] Redis: `docker compose up -d` para desbloquear el poller de backend (ya escrito, solo necesita Redis vivo).
- [ ] Registrar `fcm_token` real en `POST /api/devices` (hoy la app manda un token placeholder `no-fcm-yet-{uuid}`).
- [ ] Reforzar `AlarmReceiver` con el verify-then-ring completo (D40) ya que ahora hay timestamps frescos vía push.
- [ ] **Criterio de aceptación:** al terminar el combate anterior en la card real de ESPN, el backend detecta la transición y empuja `update`; la app reprograma la alarma local sin intervención del usuario.

---

## Notas operativas para Fable 5

- **Rama de trabajo:** `dev`. No mergear a `main` sin confirmación explícita (per `handoff.md`: "main sincronizada con dev hasta Fase MVP-launch, el pivot 7a aún no está en main").
- **No reabrir decisiones D1–D44** de `memoria/decisiones.md` sin justificar una nueva decisión numerada.
- **Actualizar `memoria/handoff.md`, `memoria/fases.md` y `memoria/bitacora.md`** al final de cada sesión de trabajo de Fable 5, siguiendo el formato ya establecido (es una convención estricta del repo, hay un git hook que lo verifica).
- Comandos de referencia (backend y compilación) ya documentados en detalle en `memoria/handoff.md` líneas 208–247 — reutilizar tal cual, adaptando rutas de esta máquina.
- Antes de escribir código nuevo, revisar si algo similar ya existe (ej. `AlarmService` de Fase E ya está hecho, solo falta el `Scheduler`/`Receiver`/`Activity` alrededor).

## Aparte — hallazgos operativos no bloqueantes

1. **El remote de git de esta máquina tiene el token de GitHub embebido en la URL en texto plano** (`https://ghp_...@github.com/theni55/DespertarME.git`). Funciona, pero si se comparte el `.git/config` o un log de terminal sin darse cuenta, se expone la credencial. Recomendado pasar a SSH o a un credential manager cuando haya un momento — no es urgente pero sí buena práctica.
2. La virtualización de esta máquina dio una lectura ambigua (`HyperVisorPresent: True` pero `VirtualizationFirmwareEnabled: False`) — vale la pena confirmarlo en la BIOS antes de instalar Android Studio, para no descubrir el problema a mitad de la Fase A.
