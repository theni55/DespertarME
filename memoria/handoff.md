# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

---

## Última sesión

**Fecha:** 2026-07-24 · **Sesión 23 (cont.) — Backend tenis completo. Pipeline verificado en vivo con partido ATP real. Rama `feature/tenis`.**

**Contexto:** el backend multi-sport está funcional y verificado end-to-end con un partido ATP real (Generali Open, Bublik vs Etcheverry): el poller detectó la transición `post` del partido previo (Hanfmann vs Halys) → calculó `estimated_start = 14:39` → envió push `update`. El partido empezó a las 14:41. Falta la app Android (cambios del compañero pendientes de subir).

**Hecho en esta sesión:**
1. **T1-T5 completados** (ver fases.md): provider, dominio generalizado, DB, API multi-sport (`?sport=tennis&league=atp|wta`), poller/scheduler multi-sport.
2. **Fix de timeout en API**: saltar `AthleteResolver` para tenis (nombres inline D49) — las peticiones pasan de ~20s a ~5s.
3. **Fix de `_log_alert`**: capturar valores primitivos en vez de pasar ORM (bug MissingGreenlet en `started`).
4. **FakeRedis en dev**: `scheduler.py` usa `fakeredis.FakeRedis` cuando `APP_ENV=development` (Redis Windows 3.x es incompatible con redis-py moderno).
5. **Verificación en vivo (ATP Generali Open)**:
   - Suscripción: Bublik vs Etcheverry (178887), Center Court, `sport=tennis`
   - Previo (Hanfmann vs Halys, 178886): `in` → `post` detectado a las 14:32
   - `update` push enviado: `estimated_start = 14:39 CEST`, `confidence=high`, acierto (empezó 14:41)
   - `started` push pendiente de verificar tras fix de sesión SQLAlchemy

**Commits en `feature/tenis`:** `4a1302d`, `ca99026`, `38dd439`, + 1 pendiente (fix `_log_alert` + fakeredis + memorias).

**Pendiente (próxima sesión):**
1. Verificar push `started` al recrear suscripción con el fix de sesión SQLAlchemy.
2. App Android: cuando el compañero suba sus cambios, los endpoints ya están listos (`?sport=tennis&league=atp|wta`, DTOs con `court`, `sport`, `round_description`).
3. F1: OpenF1 requiere 9.90 EUR/mes para datos en vivo — diferido.

---

## Última sesión

**Fecha:** 2026-07-21 · **Sesión 22 — Plan de dogfooding personal (Android compañero + iOS owner) documentado en `memoria/plan-mvp-ios.md`. Sin cambios de código.**

**Contexto:** el owner quiere seguir probando la app entre él y su compañero (Android) y él mismo en iOS antes de plantear publicación. Se hizo un repaso de la deuda técnica pendiente (fases.md, decisiones.md, plan-mvp-android-fable5.md) para separar lo bloqueante de dogfooding de lo que solo aplica a publicación.

**Hecho en esta sesión:**
1. **Sync de repo**: el `dev` local estaba en Sesión 17 (`d9d9105`); `origin/dev` tenía la historia reescrita hasta Sesión 21 (`18095f3`, incluye Sesiones 18-21: Fase G/D45 FCM end-to-end, deploy Railway, diagnóstico hardware físico). `git reset --hard origin/dev` tras confirmar que el contenido de los commits locales existía igual (mismos mensajes, distinto SHA) en el remoto.
2. **Análisis de estado**: confirmado que el MVP es funcionalmente completo salvo la validación con evento real (25-jul) y Doze. Se repasó la deuda técnica conocida (UNIQUE de `alert_log` sin `message_type`, UUID v4 sin validar en `DeviceCreate`, sin auth real en `X-Device-Id`, sin fallback si se pierde un push FCM).
3. **Hallazgo nuevo (no documentado antes)**: `src/app/notifiers/fcm.py::FcmNotifier.send()` construye el mensaje con `AndroidConfig` pero **sin `ApnsConfig`** — un push data-only a un token iOS probablemente no despertará la app en background sin `content-available`+`apns-priority: 5`. Bloqueante para cualquier prueba real en iOS, ver plan.
4. **Investigación de membership Apple Developer**: confirmado en `developer.apple.com/support/compare-memberships` que la cuenta gratuita ("Personal Team") permite testing on-device pero con perfiles que caducan a los 7 días, sin ad-hoc distribution ni TestFlight (exclusivos de pago), y con "Advanced app capabilities and services" solo en la columna de pago — riesgo real para AlarmKit/Push.
5. **Plan documentado en `memoria/plan-mvp-ios.md`**: dos pistas (cierre de Android para el compañero + bootstrap de iOS), con una Fase 0 de spike de riesgo (GitHub Actions `macos-14` para compilar + AltStore/AltServer en este PC Windows para firmar/instalar sin Mac físico) antes de construir el MVP iOS completo, condicionando la decisión de pagar el Programa Apple Developer al resultado del spike.

**Pendiente de la próxima sesión** (ver `memoria/plan-mvp-ios.md` para el detalle completo):
1. Fix de backend: añadir `ApnsConfig` a `FcmNotifier.send()` (con test de regresión).
2. Fase 0 — spike iOS: proyecto Xcode mínimo + workflow GitHub Actions `macos-14` + AltServer en este PC + prueba aislada de AlarmKit y Push Notifications con Apple ID gratuita.
3. En paralelo (Android): validación con evento real 25-jul, Doze validation, sideload en el móvil del compañero.

---

## Sesión 21 (anterior)

**Fecha:** 2026-07-21 · **Sesión 21 — Diagnóstico FCM en hardware físico: pipeline verificado end-to-end. No hubo error; las suscripciones del 18-jul estaban en el emulador, no en el móvil.**

**Contexto:** el owner reportó que la app no recibió pushes FCM en el móvil físico durante el evento UFC del 18-jul. Sin acceso adb/logcat en el dispositivo, se diagnosticó remotamente desde la API de Railway + logs del backend. El análisis confirmó que el backend funcionó correctamente todo el tiempo y que FCM entrega al hardware físico sin problemas.

**Evidencia recopilada (trazable vía Railway logs y API):**

| Fuente | Dato | Conclusión |
|--------|------|------------|
| `GET /health` → 200, `GET /api/events` con datos ESPN | Backend Railway operativo | Poller corriendo cada 60s |
| Logs Railway 18-jul `grep "Push"` | 13 pushes enviados ese día: 2 suscripciones (`f538c874`, `b28e2de9`), device `3d9ef804` | **Pushes sí se enviaron**, cero errores FCM |
| `GET /api/subscriptions` con `X-Device-Id: 5c20fa0b` | `[]` (sin suscripciones activas para el móvil) | El móvil nunca fue destinatario |
| `POST /api/devices/me/test-alarm` con `5c20fa0b` → `message_id` real | **Alarma sonó en el móvil** | Pipeline FCM backend→Firebase→móvil→alarma 100% operativo |
| Nueva suscripción `455062f2` creada desde la app (bout 401898030, lead 5) | Poller envió `update` a las 14:16:08 UTC mismo día | Push `update` entregado a `5c20fa0b` (message_id real en `alert_log`) |
| `GET /api/alerts` para `5c20fa0b` | 1 alerta registrada: `message_type=update`, `estimate_start=2026-07-25T13:00+00:00`, `reason="no hay combate previo; fecha programada"` | El poller procesa suscripciones del móvil en tiempo real |

**Conclusión del diagnóstico: no hubo ningún error.** Las suscripciones y pushes del 18-jul estaban asociadas al device `3d9ef804` (el emulador `pixel_6_api34` usado en la Sesión 18 para el smoke E2E, cuyo UUID era distinto al del móvil físico). El móvil físico (`5c20fa0b`) no tenía suscripciones activas ese día, por lo que el poller nunca le envió pushes — comportamiento esperado y correcto.

**Hallazgo técnico sobre `prev=None`:** el combate suscrito (match 13 del evento 600059667) es el primero de la tarjeta, sin combate previo que rastrear. En este caso, el `EstimatorEngine` cae a la fecha oficial de ESPN como estimación. Es el **único caso** donde se usa la hora programada (decisión del owner). Para todos los demás combates, la estimación se recalcula con el estado en vivo del combate previo (D18/D45).

**Hecho en esta sesión (diagnóstico, sin cambios de código):**
1. Verificación de salud del backend Railway (`/health`, ESPN reachable).
2. Revisión de logs del 18-jul: confirmados 13 pushes FCM reales a device `3d9ef804`, cero errores.
3. `POST /api/devices/me/test-alarm` a device `5c20fa0b` → alarma sonó en el móvil.
4. Verificación del estado de suscripciones del móvil (vacío al inicio, creada una nueva durante la sesión).
5. Confirmación de que el poller procesó la nueva suscripción y envió push `update` en el mismo ciclo (14:16:08 UTC, message_id real en `alert_log`).

**Pendiente de la próxima sesión:**
1. **Validación completa con evento real** — UFC Fight Night: Ankalaev vs Guskov, 25 julio 2026, 13:00 UTC. El poller monitorizará las transiciones ESPN del combate previo (match 14) → push `update` a `5c20fa0b` → `setAlarmClock` → alarma suena ~4 min antes del combate objetivo.
2. **Validación Doze** — `adb shell dumpsys deviceidle force-idle` + verificar `setAlarmClock` despierta puntualmente.
3. **Release keystore + baseUrl per buildType + ProGuard** — pospuesto.
4. **Play Store** — cuenta Google Play ($25) + listing + AAB firmado.

---

## Sesión 20 (anterior)

**Fecha:** 2026-07-18 · **Sesión 20 — Backend en Railway operativo. baseUrl cambiado a URL pública. APK lista para test en hardware físico.**

**Contexto:** tras varios despliegues fallidos en Railway por bugs en la migración `f7a0001_devices` (ENUMs dropeados y reutilizados en PG virgen, `op.drop_table()` sin `if_exists`), se aplicaron 3 fixes incrementales hasta que el deploy pasó. El backend responde en `https://despertarme-production.up.railway.app` con `/health` 200, `/api/events` con datos reales de UFC Fight Night Du Plessis vs Usman (12 combates, headshots, previous_bout_id server-side). Se cambió `baseUrl` en la app Android de `http://10.0.2.2:8000/` a la URL pública de Railway. APK debug recompilada (23.1 MB). FCM_CREDENTIALS_JSON configurado y SCHEDULER_ENABLED=true para que el poller corra 24/7 en Railway.

**Hecho en esta sesión:**

1. **Fix de migración `f7a0001_devices`** — (a) añadido `if_exists=True` a los 5 `op.drop_table()` (la migración era no-idempotente y fallaba en PG virgen sin log output — OOM probable en free tier). (b) Eliminado bloque `sa.Enum(name="user_role").drop()` entero (innecesario en PG virgen; `subscription_status`/`alert_status` se reciclan en el nuevo schema). (c) Ruff + black aplicados a todos los ficheros de `alembic/`. 2 commits (`f32d502`, `50aa62f`).
2. **Fix de `railway.json`** — (a) `healthcheckTimeout` subido de 120 a 300s. (b) `startCommand` eliminado (Railway no soporta shell builtins como `set`, `exec`; usa CMD del Dockerfile). (c) `--log-level debug` añadido al CMD del Dockerfile. Commit `6164820`.
3. **`.dockerignore`** creado (62 líneas): excluye `.venv/`, `mobile-kotlin/`, `mobile-expo/`, secrets, logs, caches. Commit `9a7b911`.
4. **Root cause del primer healthcheck failure** — `DATABASE_URL` en Railway tenía un espacio al final (SQLAlchemy rechaza URLs con whitespace). Tras corregir, deploy pasó a "Running".
5. **Verificación del backend** — `/health` 200, `/api/events` devuelve UFC Fight Night con datos ESPN reales, `/api/events/600059599` con 12 combates + headshots + `previous_bout_id` calculado server-side. Configurado `SCHEDULER_ENABLED=true` + `FCM_CREDENTIALS_JSON`.
6. **`baseUrl` en APK** — `AppContainer.kt:40` cambiado de `http://10.0.2.2:8000/` a `https://despertarme-production.up.railway.app/`. APK debug recompilada (BUILD SUCCESSFUL, 23.1 MB).
7. **`fcm-one-line.txt`** generado con JSON de Firebase comprimido a una línea (2345 chars), usado para pegar en Railway.
8. **Smoke emulador con APK Railway** — APK debug instalada en `pixel_6_api34` vía `adb install`. App arrancó sin FATAL: FirebaseApp inicializado OK, MainActivity displayed. `logcat` limpio sin `AndroidRuntime`. La app contacta con Railway directamente (`https://despertarme-production.up.railway.app`) sin `adb reverse` — no necesita puente al PC. El backend respondió desde el emulador vía curl (verificación externa del endpoint `/api/devices`). Sin embargo, los logs de la app (`Log.i("DespertarMe", ...)`) no se capturaron en logcat — probablemente el buffer del emulador los perdió. La app se ve funcional en pantalla.

**Pendiente de la próxima sesión:**
1. **Validación con evento real de UFC (hoy noche)** — Prelims 23:00 CEST (21:00 UTC), main card 02:00 CEST (00:00 UTC). Instalar APK en emulador o móvil físico → suscribirse a un combate → esperar push FCM real del poller en Railway → alarma suena con DnD.
2. **Validación Doze** — `adb shell dumpsys deviceidle force-idle` + verificar `setAlarmClock` despierta.
3. **Validación en hardware físico** — bypass OEM quirks. APK debug por `adb install`.
4. **Release keystore + baseUrl per buildType + ProGuard** — pospuesto. El test con evento real usa APK debug.
5. **Play Store** — cuenta Google Play ($25) + listing + AAB firmado.

---

## Sesión 19 (anterior)

**Fecha:** 2026-07-18 · **Sesión 19 — Polishing pre-Play Store: icono launcher custom + limpieza de código + memorias actualizadas.**

**Contexto:** el owner preguntó cuánto quedaba para terminar la app. Tras revisión completa del código de `mobile-kotlin/` (27 ficheros Kotlin + manifest + resources) se confirmó que **el código de features está terminado** desde Sesión 18 (Fase G completada con pipeline FCM end-to-end verificado en emulador). Esta sesión fue de pulido pre-Play-Store, no de features.

**Hecho en esta sesión:**

1. **Icono de launcher propio** — adaptive icon vectorial (sin PNGs por densidad, `minSdk=26` lo permite): `res/drawable/ic_launcher_background.xml` (fondo rojo `#E50914`) + `res/drawable/ic_launcher_foreground.xml` (Material `ic_alarm` blanco escalado a safe zone de 108dp) + `res/mipmap-anydpi-v26/ic_launcher.xml` + `ic_launcher_round.xml`. `AndroidManifest.xml` actualizado: `@android:drawable/sym_def_app_icon` sustituido por `@mipmap/ic_launcher` + `@mipmap/ic_launcher_round`.
2. **PNG 512×512 para Play Console** — `scripts/gen_playstore_icon.ps1` commiteable (PowerShell + `System.Drawing`) genera `mobile-kotlin/app/src/main/playstore-icon.png` con fondo rojo + reloj de alarma blanco. Placeholder mejorable con logo real del owner.
3. **Limpieza de código en `AlarmActivity.kt`** — borradas 3 líneas de imports sin usar: `kotlin.time.Duration.Companion.minutes`, `kotlin.time.DurationUnit`, `kotlinx.coroutines.runBlocking`.
4. **Limpieza de dead code en `DespertarMeApp.kt`** — borrado bloque `val attrs` con `@Suppress("unused")` (4 líneas de `AudioAttributes` que nunca se asignaban al channel).
5. **Comentario stale actualizado en `AppContainer.kt`** — "FCM placeholder until the FCM tramo arrives" sustituido por texto que refleja que FCM está wired desde Sesión 18 y el placeholder sigue siendo válido para el caso pre-`onNewToken`.
6. **Deuda documental cerrada en `memoria/fases.md`** — Paso 4 (Tramo FCM) y AlarmScreen marcados `[x]` con notas "(Sesión 18: ...)".

**Pendiente de la próxima sesión:**
1. ⭐ **Deploy Railway (prerrequisito para todo lo demás)** — el owner crea cuenta Railway → despliega `theni55/DespertarME` (rama `dev`) → añade add-ons Postgres + Redis → configura env-vars (`FCM_CREDENTIALS_JSON` desde `.firebase-service-account.json`, `APP_ENV=production`, `JWT_SECRET`) → obtiene URL pública tipo `https://despertarme-production.up.railway.app/`. `railway.json` ya existe. El proyecto usa Dockerfile de producción con `alembic upgrade head` en start command. **Bloquea los items 2 y 3.**
2. **Cambiar `baseUrl` en `AppContainer.kt`** — reemplazar `http://10.0.2.2:8000/` por la URL HTTPS de Railway (~1 línea). Recompilar APK debug → instalar en móvil físico del owner vía `adb install`. Sin este cambio, el móvil físico no puede contactar al backend (10.0.2.2 solo funciona en emulador).
3. **Validación en hardware físico + evento real de UFC** — el UFC Fight Night: Du Plessis vs Usman (prelims 23:00 CEST, main card 02:00 CEST 19 jul). Suscribirse a un combate con `bout_id` actual desde la app en el móvil físico → esperar push FCM real del poller corriendo en Railway → alarma suena con DnD activado + Doze validado en hardware OEM real.
4. **Validación Doze emulador** — `adb shell dumpsys deviceidle force-idle` (opcional, ya se validará en hardware físico en el item 3).
5. **Release keystore + `baseUrl` per buildType + ProGuard** — pospuesto (no bloquea test en móvil físico con APK debug). Entra en el tramo final pre-Play-Store.
6. **Play Store** — cuenta Google Play ($25) + listing (icono PNG 512 ya generado, screenshots + descripción + política de privacidad pendientes) + subir AAB firmado.
7. **Mejoras post-MVP pospuestas**: sonido custom `alarm.ogg`, Home póster dinámico del próximo evento (D42), admin web de devices, calibrado buffer inter-combates.

---

## Sesión 18 (anterior)

**Fecha:** 2026-07-17/18 · **Sesión 18 — Fase G: modelo de alarma revisado D45. Pipeline FCM end-to-end verificado: backend → push FCM → app → alarma suena + AlarmActivity. Cushion siempre +1 min, ring-once con flag `fired`. Smoke E2E en emulador OK (alarma sonó a los 6 min de recibir push `update` simulado).**

**Contexto:** el owner pidió revisar el modelo de alarma de la Sesión 17. Tras grilling iterativo (plan mode) se llegó al modelo D45: la alarma local NO se programa al suscribirse; el backend solo manda push `update` cuando el combate previo transiciona `pre→in` o `in→post` (no en `pre`). La app programa la alarma al recibir el push, con cushion siempre +1 min y ring-once (flag `fired=true`). Lead=30 suena al recibir primer push (pre→in) + cushion; lead=10/15 suenan juntos al acabar el previo (~9 min aviso); lead=5 suena ~4 min antes. Sin fallback a fecha oficial de ESPN (decisión del owner). Opción 60 min eliminada del selector.

**Hecho en esta sesión:**

1. **Backend `poller.py`** — (a) Guard D45: skip push `update` cuando `prev_status.state == "pre"` (solo se pushea cuando prev está `in` o `post`). (b) `estimated_start_at` ahora es epoch millis (str de un int), no ISO string — Android parse con `toLongOrNull()`.
2. **Backend `scheduler.py`** — `EstimatorConfig(buffer_intercombate_seconds=settings.buffer_intercombate_seconds)` wired al Poller. Antes el estimador usaba su hardcoded 300s ignorando `.env`.
3. **`.env` + `.env.example`** — `BUFFER_INTERCOMBATE_SECONDS=300` → `600` (10 min reales entre combates, confirmado por el owner).
4. **`tests/test_poller.py`** — 3 tests ajustados (guard pre-vs-push, epoch millis parse). 80/80 verdes.
5. **Android `PendingAlarm.kt`** — añadido campo `fired: Boolean = false`.
6. **Android `EventDetailViewModel.kt`** — eliminada la pre-programación al suscribirse. Ahora solo persiste `PendingAlarm(triggerAtMillis=0L, fired=false)` como centinela. Snackbar: *"Te avisaremos N min antes cuando el backend detecte el inicio real"*.
7. **Android `EventDetailScreen.kt`** — `LEAD_OPTIONS` reducido a `listOf(5, 10, 15, 30)` (quitado 60 — "demasiado difícil de predecir").
8. **Android `DespertarMeFirebaseService.handleUpdate()`** — reescrito con lógica D45: si `fired=true` → ignora. Si lead>=30 y ya programado → ignora. Si lead>=30 → `trigger = now + 60s`. Si lead<30 → `trigger = max(now+60s, est-lead+60s)`. Siempre cushion +1 min.
9. **Android `DespertarMeFirebaseService.cancelAlarmAndNotify()`** — ahora marca `fired=true` antes de cancelar.
10. **Android `AlarmReceiver.kt`** — simplificado: sin verify-then-ring (ya no necesario, las alarmas solo se programan con estimación real del backend). Marca `fired=true` al disparar.
11. **`memoria/decisiones.md`** — registrada D45 con el modelo completo.
12. **Firebase setup completado por el owner:** `console.firebase.google.com` → proyecto `despertarme-73d00` → service account JSON + `google-services.json`. Ficheros colocados en `.firebase-service-account.json` (root, gitignored) y `mobile-kotlin/app/google-services.json` (commiteable).
13. **Backend FCM verificado:** `build_notifier()` devuelve `FcmNotifier` (no Dummy). Smoke con token fake recibió `InvalidRegistration` (esperado) → credenciales válidas, falta token real.
14. **Android Firebase wired:** plugin `com.google.gms.google-services` + `firebase-messaging-ktx:24.1.0` añadidos a `build.gradle.kts` y `libs.versions.toml`. Build verde con `google-services.json` procesado.
15. **Docker Desktop + Redis arrancados:** `docker compose up -d redis`. Poller consultando ESPN cada 60s (verificado en `uvicorn.err`: "Job PollerScheduler._poll_job executed successfully"). Las 7 suscripciones de sesiones previas apuntan a bout_id que ya no existe en ESPN → el poller las salta (warning "Combate 401566093 no encontrado en la card") sin crashar.
16. **Emulador + APK + FCM token real:** `pixel_6_api34` arrancado, APK instalado, permisos `POST_NOTIFICATIONS` concedidos. La app obtiene token real `e_f7hyAY...` vía `FirebaseMessagingService.onNewToken()` y lo registra con el backend (`POST /api/devices` upsert). Logcat: "Nuevo FCM token: ..." + "FCM token registrado con el backend".
17. **Smoke `POST /api/devices/me/test-alarm` E2E OK:** backend envió push `fire` con message_id `projects/despertarme-73d00/messages/0:1784323051075181%...`. App recibió `FCM message type=fire` → AlarmService foreground → AlarmActivity abierta → `AudioTrack frames delivered` (sonando). Pipeline completo backend-FCM-app-sonido-pantalla verificado.
18. **Smoke endpoint debug `/api/debug/simulate-transition`** (temporal, borrado tras el test): simuló push `update` con `estimated_start_at = now + 10 min` para una suscripción real (lead=5) creada desde la app.
    - A las 22:12:31 el backend mandó push al token real del emulador.
    - App recibió → `handleUpdate()` calculó `trigger = max(now+1min, (now+10min) - 5min + 1min) = now+6min` → `AlarmScheduler.schedule(trigger=now+6min)` → `setAlarmClock` registrado en `dumpsys alarm` (RTC_WAKEUP #7 com.despertarme.app, tag=*walarm*:com.despertarme.app.action.ALARM_FIRE).
    - A las 22:18:32 (6 min 2 s después) → `AlarmReceiver: Alarma disparada y fired=true marcado para bout=401889642` → `AlarmActivity` abierta sobre lockscreen → `AlarmService` arrancado (TYPE_ALARM sonando, `AudioTrack frames delivered`).
    - Verificación `dumpsys alarm`: entrada histórica `+76ms running, 1 wakeups` (alarma disparada).
    - Pipeline D45 completo **VERIFICADO END-TO-END en emulador**.
19. **Limpieza:** `src/app/api/routes/debug.py` y bloque `if app_env=="development"` en `main.py` borrados tras confirmar el test. `pytest` 80/80 verdes tras el borrado.

**Pendiente de la próxima sesión:**
1. **Validación con evento real de UFC** — el UFC Fight Night: Du Plessis vs Usman es el 18 de julio (prelims a las 23:00 CEST, main card a las 02:00 CEST del 19). El poller ya está cableado y correrá. Suscribirse a un combate desde la app y esperar a las transiciones reales de ESPN para validar el flujo completo (no simulado). **Limitación**: las suscripciones de smoke previas apuntan a un `bout_id` que ya no existe en ESPN — hay que crear suscripciones nuevas a los bout_ids actuales (401872218, 401874062, etc.).
2. **Validación en hardware físico del owner** — bypass DnD real + OEM quirks (algunos OEMs chinos matan FCM en background).
3. **Fase 7c (deploy Railway)** — pendiente cuando el owner tenga cuenta. `railway.json` ya existe desde Sesión 5. Solo falta setear `FCM_CREDENTIALS_JSON`, `DATABASE_URL`, `REDIS_URL` + cambiar `baseUrl` de la APK a la URL pública de Railway.
4. **Validación Doze** — `adb shell dumpsys deviceidle force-idle` + verify `setAlarmClock` dispara puntualmente (Doze exento por diseño Android). Aún pendiente.

---

## Sesión 17 (anterior)

**Fecha:** 2026-07-17 · **Sesión 17 — Fases B+C+D del plan MVP Android completadas: backend local operativo (fix SSL corporativo), bottom nav + 4 pantallas navegables, suscribir/cancelar E2E verificado en emulador.**

**Contexto:** goal de OpenCode agrupando Fases B, C y D de `memoria/plan-mvp-android-fable5.md` (decisión del owner: "agrupar b c y d").

**Hecho en esta sesión:**

1. **Fase B — backend local:** venv/`.env` SQLite ya existían de Sesión 16; `alembic upgrade head` (head `f7a0001_devices`) + uvicorn `--host 0.0.0.0`. **Quirk crítico de esta máquina:** el proxy TLS corporativo (CA self-signed) rompía ESPN con `CERTIFICATE_VERIFY_FAILED` → fix con `pip install truststore` + `sitecustomize.py` en `.venv/Lib/site-packages/` (`truststore.inject_into_ssl()`, usa el cert store de Windows). El venv es gitignored — **si se recrea el venv hay que repetir este fix**. Criterios verificados: `POST /api/devices` 201, `GET /api/events/600059599` con 12 combates reales.
2. **Fase D — cliente API:** `DespertarApi.kt` + `deleteSubscription` (`@DELETE`) + `listAlerts` (`@GET` con limit) + DTO `AlertLogOut` en `Models.kt`.
3. **Fase C — NavigationBar:** Material3 con 4 destinos (Home/Eventos/Mis Alertas/Ajustes), acento `UfcRed`, patrón `popUpTo(findStartDestination){saveState}+launchSingleTop+restoreState`. `AppGraph` reescrito con `Scaffold`.
4. **Fase D — pantallas nuevas:** `EventListScreen`+`EventListViewModel` (tarjetas con franja degradada roja — ESPN no sirve `image_url`, D42), `SubscriptionsScreen`+`SubscriptionsViewModel` (activas con nombres de peleadores resueltos vía fetch del evento + cancelar + historial de alertas), `SettingsScreen` (device_id, timezone, permisos, toggle probar alarma).
5. **Fase C — pulido BoutCard:** badge segmento con color (main rojo/prelims azul), chip "PRÓXIMO" + borde rojo en el primer combate (el backend lista en orden cronológico). Fix deprecación `ArrowBack` → AutoMirrored. Fuente Inter: evaluada y **diferida** (binarios TTF sin beneficio claro en esta fase).
6. **`AlarmService.ACTION_STOP` (extra):** el smoke destapó que no había forma de silenciar el sonido de prueba desde la app (solo `ACTION_START`; el owner tuvo que pedir pararla). Añadido `ACTION_STOP` + toggle "Probar/Parar" en Home y Ajustes. Verificado: service arranca y para desde UI.
7. **Smoke E2E en emulador** (`pixel_6_api34`): build verde sin warnings; recorrido Home → Eventos → EventDetail → suscribir (`POST` 201) → Mis Alertas muestra "Anna Melisano vs Dione Barbosa · 15 min antes" → cancelar (`DELETE` 204, snackbar) → empty state; Ajustes con permisos en verde; logcat sin FATAL en todo el recorrido. Capturas revisadas visualmente contra las referencias Winamax.

**Pendiente de la próxima sesión** (plan `plan-mvp-android-fable5.md`):
1. **Fase E** — alarma v1 un solo disparo: `AlarmScheduler` (`setAlarmClock`), `AlarmReceiver` + verify-then-ring básico, `AlarmActivity` full-screen (puede reutilizar `ACTION_STOP`), `BootReceiver`, validación Doze.
2. Fase F — validación end-to-end del MVP completo.
3. Fase G sigue bloqueada por setup Firebase manual del owner (~30 min).

---

## Sesión 16 (anterior)

**Fecha:** 2026-07-17 · **Sesión 16 — Fase A del plan MVP Android completada en la máquina `javier.romero`: entorno Android operativo (Android Studio + SDK + AVD + build verde).**

**Contexto:** primera sesión en la máquina nueva (`javier.romero`, Windows — la anterior era `pacor`). Se ejecutó como goal de OpenCode (`/goal` plugin) la Fase A de `memoria/plan-mvp-android-fable5.md`.

**Hecho en esta sesión:**

1. **Virtualización verificada:** hipervisor activo (`hvservice` + `vmcompute` corriendo, WSL2 Ubuntu). El `VirtualizationFirmwareEnabled=False` de `Win32_Processor` era el falso negativo esperable con Hyper-V on. `emulator -accel-check` → **"WHPX(10.0.26100) is installed and usable"**. No se instaló HAXM.
2. **Android Studio 2026.1.2.10** instalado vía `winget install Google.AndroidStudio` (con UAC manual del owner).
3. **SDK bootstrapeado por CLI** (sin wizard GUI): cmdline-tools descargadas a `%LOCALAPPDATA%\Android\Sdk\cmdline-tools\latest`, licencias aceptadas, `sdkmanager` instaló `platform-tools 37.0.0` + `platforms;android-34` + `build-tools;34.0.0` + `emulator 36.6.11` + `system-images;android-34;google_apis;x86_64`. (Quirk: la descarga del zip con `Invoke-WebRequest` se truncó a 79 MB; `curl.exe -C -` la completó a 136 MB.)
4. **Variables de entorno:** `ANDROID_HOME` (User) + `platform-tools`/`emulator`/`cmdline-tools\latest\bin` en PATH User. `JAVA_HOME` (Machine) ya apuntaba al JDK 21 de Microsoft — válido (≥17), sin cambios.
5. **AVD `pixel_6_api34`** creado con `avdmanager` (Pixel 6, API 34, Google APIs x86_64) — mismo nombre que en la máquina anterior, comandos del handoff reutilizables.
6. **`local.properties`** creado con `sdk.dir` (gitignored) y **`app/debug.keystore` regenerado** con `keytool` (gitignored — el del otro PC no se versiona; params estándar `androiddebugkey`/`android`).
7. **Build:** `gradlew assembleDebug` → **BUILD SUCCESSFUL** (primera pasada falló solo por el keystore ausente; tras regenerarlo, verde en 1m 10s).
8. **Emulador:** AVD arrancado, "Windows Hypervisor Platform accelerator is operational", `adb devices` → `emulator-5554 device`, `sys.boot_completed=1`, Android 14. Warnings benignos (opengl32sw fallback, snapshot inexistente en primer boot).
9. `.gitignore` raíz: añadido `.opencode/goals/` (estado local del plugin `/goal` de OpenCode).

**Rutas de esta máquina (difieren del handoff anterior):**

```powershell
# JAVA_HOME (Machine, ya fijado): C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot
# ANDROID_HOME (User, ya fijado): C:\Users\javier.romero\AppData\Local\Android\Sdk
# Repo: C:\Users\javier.romero\Personal\DespertarME

& "C:\Users\javier.romero\Personal\DespertarME\mobile-kotlin\gradlew.bat" -p "C:\Users\javier.romero\Personal\DespertarME\mobile-kotlin" assembleDebug --no-daemon --console=plain
emulator -avd pixel_6_api34 -no-snapshot-save -no-boot-anim
```

**Pendiente de la próxima sesión** (plan `plan-mvp-android-fable5.md`):
1. **Fase B** — backend local operativo (venv + `.env` SQLite + alembic + uvicorn + `adb reverse`).
2. Fase C/D — sistema visual + pantallas restantes.
3. Fase E — alarma v1 un solo disparo.
4. Fase G sigue bloqueada por setup Firebase manual del owner.

---

## Sesión 15 (anterior)

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

## Sesión 15 (cont.)

**Fecha:** 2026-07-16 · **Sesión 15 (cont.) — Fixes visuales commiteados. Alarma bloqueada: requiere setup Firebase (manual owner, ~30 min).**

### Fixes visuales (commit a055231)

- Home reestructurado: hero `ContentScale.Fit` arriba (poster McGregor vs Holloway completo, ambos peleadores visibles, sin recortar) + zona inferior fija sobre `BackgroundDark` sólido con título + botones. `windowInsetsPadding(WindowInsets.safeDrawing)` para que "Avísame" no quede ocluido bajo las barras del sistema.
- `AthleteColumn` con placeholder de iniciales para peleadores sin headshot (debutantes/prelims — ESPN no siempre resuelve). Patrón equivalente al SVG placeholder de la web (Sesión 5).
- Owner aceptó el Home como está: "se quedará así la imagen, no es tan relevante en esta fase".
- Tap en nueva zona inferior dispara navegación Home→EventDetail: verificado `GET /api/events/600059599` desde puerto nuevo en `uvicorn.out`. Sin FATAL.

### ⚠️ Bloqueo crítico: alarma funcional requiere FCM (manual del owner)

El owner pidió: **"la alarma tiene que funcionar en este v1"** y aclaró el objetivo real de la app:

> "no es para que te avise a la hora que este programada la pecha, el objetivo de esta app era seguir en tiempo real los combates para cuando acabe el anterior avisarte exactamente cuando empieza el siguiente (el tiempo de antes que le pongas)"

Revisando el código del Poller + decisiones D40 confirmé que la app se diseñó literalmente para esto: el backend hace polling de ESPN en vivo (cada 60s) y cuando el combate previo termina (transición `in→post`), recalcula `estimated_start_at = observed_at + 5 min buffer (D18)` y envía push FCM `update` con el nuevo timestamp. La app recibe el push y **reprograma** `AlarmManager.setAlarmClock()` al nuevo momento.

**El flujo es imposible sin FCM:**
- Con un `AlarmScheduler` de un solo disparo con `bout.date` (lo que yo propuse), la alarma sonaría a la hora programada oficial, no a la real. Si el combate previo se alarga, la alarma suena antes de tiempo. Es solo un calendador — no resuelve el caso de uso central.
- FCM es la única vía de que el backend informe a la app *"la estimación cambió, reprograma la alarma"*, y se disparará cuando ESPN detecta la transición `in→post` del previo. Cada push `update` lleva `estimated_start_at` fresco.

### Botón "Probar sonido" — se deja

Owner decidió: **dejarlo por ahora para comprobar que funciona (como en el primer spike)**. Se quitará cuando entre FCM y el `AlarmScheduler` real. Por ahora cumple la función de debug que tenía el spike Expo — verificar que `AlarmService` + `setBypassDnd` + `USAGE_ALARM` siguen funcionando tras reinicios/reinstalaciones.

### Decisión de cierre

Parar la sesión aquí. La próxima arranca por **setup Firebase manual del owner (~30 min en console.firebase.google.com):**

1. Crear proyecto `despertarme` en console.firebase.google.com.
2. Habilitar Cloud Messaging (Engagement → Messaging o Build → Cloud Messaging).
3. **Service account key Python (backend):** Project settings → Service accounts → Generate new private key → descargar JSON. Guardar contenido en `.env` como `FCM_CREDENTIALS_JSON=< contenido pegado en una sola línea >` (o `FCM_CREDENTIALS_PATH` apuntando al fichero). Sin esto, `build_notifier()` sigue cayendo a `DummyNotifier` y los push se logean pero no se envían.
4. **`google-services.json` para Android:** Project settings → "Add app" → Android → package name `com.despertarme.app` → descargar y pegar en `mobile-kotlin/app/`.
5. No hace falta crear campañas ni nada — solo activar la API FCM v1 HTTP y obtener las dos credenciales.

Tras eso, codeo en paralelo:
- **(a) Backend:** `notifiers/fcm.py` ya soporta firebase-admin cuando las env-vars están — solo necesita el JSON. `build_notifier()` gatea correctamente (fix Critical Sesión 13 ya aplicado).
- **(b) Cliente Android FCM:** `FirebaseMessagingService` Kotlin que parsea data-only payload `type=update|started|cancelled`, reprograma `AlarmScheduler.schedule(newEstimatedStartAt)` (update), muestra notificación informativa (started/cancelled), o arranca `AlarmService` (started si algo se pasó).
- **(c) `AlarmScheduler`:** `AlarmManager.setAlarmClock()` a `estimatedStartEpochMillis − leadMinutes*60_000`. Persistencia del `PendingAlarm` en DataStore (para que `BootReceiver` lo reprograme tras reboot). Método `schedule()` que cancela antes la alarma anterior — solo puede haber una programada.
- **(d) `AlarmReceiver` + verify-then-ring:** al disparar, fetch `GET /api/events/{eventId}` → comprobar que el combate sigue `pre` y `bout.date` plausible → arrancar `AlarmService` (sonido). Si ya empezó (`bout.date < now`), callarlo. Si se movió más de 5 min, reprogramar. Self-healing ante FCM perdidos.
- **(e) `AlarmActivity` full-screen (post-MVP):** "X vs Y — UFC {event} empieza en ~N min" + botón "Descartar" (stop service).
- **(f) `BootReceiver`** (`RECEIVE_BOOT_COMPLETED` ya en manifest): reprogramar tras reboot.
- **(g) Redis:** `docker compose up -d` para desbloquear el poller (AlertState con idempotencia D16).

### Objetivo del producto (registro permanente)

> **El objetivo de DespertarME es avisar al usuario X minutos antes de que un combate de una tarjeta escalonada (MMA/Boxeo/Tenis) empiece realmente, siguiendo en tiempo real el combate anterior y recalculando el inicio estimado en cada transición de estado.**

- **No** debe avisar a la hora oficial programada (eso ya lo hace cualquier calendador).
- **No** depende de horarios fijos — sigue `pre → in → post` del combate previo y estima `start_objetivo ≈ now + restante + 5 min buffer` (D18).
- **La alarma local exacta** (`AlarmManager.setAlarmClock` en Android / AlarmKit en iOS 26+ según D40) es la fuente de verdad del "cuándo sonar", independiente del backend. El backend **solo** la mantiene fresca vía push FCM `update` con `estimated_start_at`.
- **Verify-then-ring** (D40): al disparar la alarma, la app verifica que el combate sigue `pre` con estimación plausible antes de sonar, evitando sonar si se retrasó o canceló.
- **Bypass DnD / silencio obligatorio** (spike Sesión 11 validado en Android 14 físico): canal `IMPORTANCE_HIGH` + `setBypassDnd(true)` + `AudioAttributes.USAGE_ALARM` + foreground service `mediaPlayback`. iOS vía AlarmKit (no requiere Critical Alert Entitlement).

Sin FCM, las dos últimas (reprogramar en tiempo real y verify-then-ring con timestamp fresco) no son posibles. Setup Firebase es el desbloqueante.

### Commits

- `a055231` ya aplicado: fix visual Home + placeholder headshots + insets.
- Esta sesión-cierre commitea solo memorias: `docs(memoria): Sesion 15 (cont.) - alarma bloqueada por FCM (setup owner pendiente)`.

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
| Fase MVP-launch — fotos + Twilio + scheduler + Railway | **Completada** ✅ (Railway deploy ejecutado Sesión 20) |
| Fase 4 — Boxeo/Tenis reales | Pendiente (fuera del MVP) |
| Fase 5 — VoiceNotifier real (Twilio) | ❄️ **Obsoleta** — sustituida por FCM (D37/D40) |
| Fase 6 — Rediseño visual + landing dinámica | ❄️ **Congelada** — rama `web` |
| Fase 7 — App móvil | 🔶 **En curso** — Spike ✅, Fase 7a (backend Device/FCM) ✅, scaffold Kotlin (D43) ✅, Fase G (alarma D45) ✅, Railway deploy ✅. **Sesión 21: pipeline FCM verificado end-to-end en hardware físico (test-alarm sonó + push update del poller entregado).** **Sesión 22: plan de dogfooding Android+iOS documentado en `plan-mvp-ios.md`** (spike de riesgo iOS pendiente + fix `ApnsConfig` en backend). Publicación (Play Store/App Store) diferida explícitamente. |

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

## Cómo compilar y arrancar la app Android (máquina `javier.romero`, desde Sesión 16)

```powershell
# Env vars ya persistidas: JAVA_HOME (Machine) = C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot
#                          ANDROID_HOME (User) = C:\Users\javier.romero\AppData\Local\Android\Sdk
#                          PATH User incluye platform-tools + emulator + cmdline-tools\latest\bin

# Compilar
& "C:\Users\javier.romero\Personal\DespertarME\mobile-kotlin\gradlew.bat" -p "C:\Users\javier.romero\Personal\DespertarME\mobile-kotlin" assembleDebug --no-daemon --console=plain

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

> Rutas de la máquina anterior (`pacor`, Sesiones 10-15): JDK 17 portable en `C:\Users\pacor\AppData\Local\jdk-17\...` y repo en `X:\Project IA\DespertarME` — ya no aplican en esta máquina.

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