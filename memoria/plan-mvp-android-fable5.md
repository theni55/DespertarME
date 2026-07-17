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

- [ ] Verificar virtualización real antes de instalar nada: `systeminfo` mostró un hipervisor ya presente pero `Win32_Processor.VirtualizationFirmwareEnabled = False` (inconsistente). Comprobar en la BIOS/UEFI que **VT-x/AMD-V** esté activado; si Windows tiene Hyper-V o WSL2 activo, el emulador Android usará **WHPX** en vez de HAXM (HAXM es incompatible con Hyper-V activo — no intentar instalarlo si Hyper-V está on).
- [ ] Instalar **Android Studio** completo (última versión estable, ej. vía `winget install Google.AndroidStudio` o descarga manual) — decisión del owner: quiere el IDE completo, no solo CLI.
- [ ] Durante el setup wizard de Android Studio: instalar **SDK Platform 34**, **Build-Tools 34/35**, **Platform-Tools**, **Emulator**, **cmdline-tools (latest)**.
- [ ] Crear un **AVD** (ej. Pixel 6, API 34, Google APIs x86_64) con aceleración por hardware (WHPX/Hyper-V).
- [ ] Configurar JDK: el proyecto requiere **JDK 17** (`compileOptions`/`kotlinOptions` en `app/build.gradle.kts` fijan `JavaVersion.VERSION_17`). Esta máquina ya tiene un JDK 21 de Microsoft instalado (`C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot`) pero **no está en `JAVA_HOME`/`PATH`** (el `java` del PATH actual resuelve a un JRE 8 antiguo). Usar el JDK embebido de Android Studio (`Android Studio\jbr`, normalmente JDK 17/21) como `JAVA_HOME` del proyecto, o fijar el JDK 21 de Microsoft — cualquiera de los dos sirve mientras sea ≥17.
- [ ] Establecer variables de entorno de usuario: `ANDROID_HOME` (SDK), `JAVA_HOME`, y añadir `platform-tools` + `emulator` al `PATH`.
- [ ] Abrir `mobile-kotlin/` como proyecto existente en Android Studio (**File → Open**, no "New Project" — el scaffold ya existe a mano, no usar wizard que sobrescriba). Dejar que Gradle sync descargue dependencias.
- [ ] **Criterio de aceptación:** `./gradlew assembleDebug` compila `BUILD SUCCESSFUL` desde Android Studio o terminal, y el AVD arranca sin errores de aceleración de hardware.

## Fase B — Backend local operativo

**Objetivo:** tener la API FastAPI corriendo en local con datos reales de ESPN, accesible desde el emulador.

- [ ] Seguir el setup de `AGENTS.md` (raíz del repo, no `mobile-kotlin/`): `python -m venv .venv`, `pip install -e .[dev]`, copiar `.env.example` → `.env` con `DATABASE_URL=sqlite+aiosqlite:///./avisador.db`.
- [ ] ⚠️ Ejecutar `alembic upgrade head` y `uvicorn app.main:app --reload --host 0.0.0.0` con **cwd en la raíz del repo**, no en `src/` (pydantic-settings no encuentra `.env` si no — cae a defaults Postgres y falla).
- [ ] Smoke test: `GET http://localhost:8000/health` → `{"status":"ok"}`; `GET /docs` muestra los 9 endpoints.
- [ ] Desde el emulador: `adb reverse tcp:8000 tcp:8000` (puente adicional; `10.0.2.2:8000` ya funciona nativo en AVD estándar — el `baseUrl` en `AppContainer.kt` ya apunta ahí).
- [ ] **Criterio de aceptación:** `POST /api/devices` desde curl/Postman devuelve 201; `GET /api/events/{id}` con un evento UFC real devuelve combates con nombres.

## Fase C — Sistema visual (aplicar la referencia de estilo)

**Objetivo:** que Home y EventDetail se vean con la densidad/impacto visual de las capturas de referencia (tarjetas con foto a toda anchura, tipografía bold, acento rojo, navegación inferior), sin romper lo que ya funciona.

Estado actual: tema ya define `UfcRed #E50914`, `BackgroundDark #0A0A0A`, tarjetas con `SurfaceDark`, columnas rojo/azul con avatar circular + iniciales de fallback. Esto es un buen punto de partida — **no reescribir desde cero**, evolucionar:

- [ ] **Bottom navigation bar** (patrón Winamax: Home / Buscar / Video / Notas / Trofeo): adaptar a **Home / Eventos / Mis Alertas / Ajustes**, con `NavigationBar` de Material3, iconos Material Icons Extended (ya en las deps). Integrar en `MainActivity.kt` (`AppGraph`) envolviendo el `NavHost` actual.
- [ ] **HomeScreen**: revisar si el hero a pantalla completa puede ganar más peso visual tipo tarjeta Winamax (imagen del evento + overlay degradado + nombre corto del evento + hora superpuesta), manteniendo el botón "Avísame" como CTA principal. No tocar la decisión ya cerrada del owner en Sesión 15 ("se quedará así la imagen, no es tan relevante en esta fase") sin confirmar con él primero.
- [ ] **BoutCard (EventDetailScreen)**: ya tiene la estructura correcta (foto+nombre por esquina, chips de metadata, selector de minutos). Mejoras de pulido visual:
  - Aumentar contraste/tamaño de foto de peleador (referencia: hero grande, no solo avatar 80dp) si el owner quiere más impacto tipo "cara del jugador ocupa media tarjeta" como en Winamax.
  - Badge de "cardSegment" (main/prelims) con color distintivo en vez de gris plano.
  - Considerar borde/gradiente sutil en la tarjeta del **próximo combate a suceder** (equivalente al borde verde/naranja de Winamax en el partido destacado) para diferenciarlo del resto de la lista.
- [ ] **Pantalla "Eventos"** (nueva, Fase D): usar tarjeta-lista similar a la 2ª captura (imagen de fondo + nombre competición + fecha), una tarjeta por evento próximo.
- [ ] Tipografía: evaluar si Inter (ya usada en la web congelada, rama `web`) se embebe como fuente en `res/font/` para reforzar la identidad visual con pesos bold marcados, en vez de la sans-serif del sistema.
- [ ] **Criterio de aceptación:** smoke visual manual en emulador — Home, lista de Eventos, EventDetail y Mis Alertas comparten look & feel coherente (fondo oscuro, tarjetas con foto, tipografía bold, acento rojo), navegables desde la barra inferior.

## Fase D — Pantallas y navegación completas

**Objetivo:** cerrar las pantallas que hoy faltan (documentadas como pendientes en `fases.md` Fase 7b Paso 3), reutilizando los endpoints backend ya existentes.

- [ ] **Cliente API**: añadir a `DespertarApi.kt` los dos endpoints que faltan por invocar desde Kotlin:
  ```kotlin
  @DELETE("/api/subscriptions/{id}")
  suspend fun deleteSubscription(@Path("id") id: String)

  @GET("/api/alerts")
  suspend fun listAlerts(@Query("limit") limit: Int = 50): List<AlertLogOut>
  ```
  (`AlertLogOut` DTO nuevo en `Models.kt`, mapear campos de `app/api/schemas.py::AlertLogOut` en el backend.)
- [ ] **Pantalla "Eventos"** (`ui/screens/EventListScreen.kt`): `GET /api/events`, lista de tarjetas (nombre evento + fecha + imagen si disponible), tap → navega a `event/{id}` (reutiliza `EventDetailScreen` ya existente).
- [ ] **Pantalla "Mis Alertas"** (`ui/screens/SubscriptionsScreen.kt`): `GET /api/subscriptions` (lista activas) + botón cancelar → `DELETE /api/subscriptions/{id}`; sección de historial con `GET /api/alerts`.
- [ ] **Pantalla "Ajustes"** (`ui/screens/SettingsScreen.kt`): mostrar `device_id` (debug), timezone, botón "Probar alarma" (ya existe como acción en Home — moverlo aquí o duplicar), estado de permisos (notificaciones, alarmas exactas).
- [ ] Actualizar `MainActivity.kt`/`AppGraph` con las 4 rutas del `NavHost` + `NavigationBar` de Fase C.
- [ ] **Criterio de aceptación:** las 4 pantallas navegables sin crashes; suscribirse en EventDetail hace aparecer la suscripción en "Mis Alertas"; cancelar la borra; el historial de alertas se lista (vacío es aceptable si no ha sonado ninguna).

## Fase E — Alarma funcional v1 (sin FCM, un solo disparo)

**Objetivo:** que el botón "Avisarme" programe una alarma real del sistema que suene a la hora estimada — hoy solo persiste la suscripción en BD, no programa nada local.

- [ ] **`AlarmScheduler`** (`alarm/AlarmScheduler.kt`, nuevo): `AlarmManager.setAlarmClock()` a `estimated_start_at − lead_minutes` (usar el timestamp que ya devuelve `GET /api/events/{id}` en el bout). Cancelar cualquier alarma previa para el mismo `bout_id` antes de reprogramar (solo una activa por combate).
- [ ] Persistir la alarma programada en DataStore (`PendingAlarm`: bout_id, event_id, trigger_at_millis) para que un `BootReceiver` pueda reprogramarla tras reinicio del dispositivo.
- [ ] **`AlarmReceiver`** (`BroadcastReceiver`): al disparar, hacer un fetch rápido a `GET /api/events/{eventId}` (verify-then-ring básico): si el combate objetivo sigue con estimación plausible → arrancar `AlarmService` (ya existe, solo sonido) + lanzar `AlarmActivity`; si el estado indica que ya empezó o se pospuso, no sonar (o sonar igual con aviso, a decidir con el owner si el margen es MVP-aceptable sin la lógica completa de D40).
- [ ] **`AlarmActivity`** (pantalla full-screen sobre lockscreen): `setShowWhenLocked(true)` + `setTurnScreenOn(true)`, texto "X vs Y — empieza en ~N min", botón "Descartar" que para `AlarmService`. Requiere permiso `USE_FULL_SCREEN_INTENT` (ya está en el manifest).
- [ ] **`BootReceiver`** (`RECEIVE_BOOT_COMPLETED`, ya declarado en manifest): al reiniciar el dispositivo, leer las `PendingAlarm` de DataStore y volver a llamar a `AlarmScheduler`.
- [ ] Conectar `EventDetailViewModel.subscribe()` (ya existente) para que, tras el `POST /api/subscriptions` exitoso, llame a `AlarmScheduler.schedule(...)` con el timestamp calculado en el momento de la suscripción.
- [ ] **Validación Doze:** `adb shell dumpsys deviceidle force-idle` en el emulador → confirmar que `setAlarmClock` sigue disparando puntualmente (este tipo de alarma está exento de Doze por diseño de Android).
- [ ] **Criterio de aceptación (end-to-end en emulador):** suscribirse a un combate con lead corto (ej. 1-2 min con hora del sistema adelantada para test) → la alarma suena con `AlarmActivity` en pantalla, incluso con el emulador en modo No Molestar/Doze forzado.
- [ ] ⚠️ **Nota honesta para el owner:** esta fase NO cumple el objetivo de producto completo ("seguir el combate anterior en tiempo real y reprogramar"). Es un calendador con hora fija tomada en el momento de suscribirse. Si el combate previo se alarga, la alarma sonará antes de tiempo. Eso solo se resuelve en la Fase G (FCM). Merece la pena dejarlo explícito en el propio commit/PR para que no se confunda con el "v1 terminado" del objetivo real.

## Fase F — Validación end-to-end del MVP

- [ ] Backend local + emulador arrancados según Fases A/B.
- [ ] Recorrido completo manual: Home → Eventos → EventDetail → suscribirse → Mis Alertas muestra la suscripción → Ajustes → Probar alarma suena con bypass DnD → esperar disparo real de una alarma de prueba con lead corto → AlarmActivity aparece → Descartar detiene el sonido.
- [ ] Revisar `logcat` sin `FATAL`/`AndroidRuntime` durante todo el recorrido.
- [ ] Capturar pantallas del resultado final para comparar visualmente contra las 3 referencias de Winamax en `memoria/assets/` (composición de tarjeta, contraste, navegación).
- [ ] **Definition of Done del MVP visual+funcional:** 4 pantallas navegables con estilo coherente, suscripción real contra el backend, alarma de un solo disparo sonando con bypass de silencio en el emulador, sin crashes.

## Fase G — Reprogramación en tiempo real vía FCM (bloqueada por acción manual, fase 2)

**No empezar hasta que el owner complete el prerrequisito manual.** Documentado aquí para que Fable 5 lo retome sin perder contexto.

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
