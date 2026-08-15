# Plan de correccion tras auditoria de fiabilidad

> Auditoria de `dev` tras integrar 101 commits remotos: inventario priorizado de bugs actuales y plan ejecutable para corregirlos en sesiones futuras.

## Alcance y estado verificado

- Rama auditada: `dev` en `206b3ab` (sin cambios locales previos).
- Backend: `ruff` limpio; `pytest` 178/179; `mypy` falla; `black --check` falla en 4 ficheros.
- Android: `assembleDebug` y `testDebugUnitTest` verdes.
- La prueba Android existente es solo `2 + 2 = 4`; el pipeline de alarmas no tiene tests automatizados.
- No se corrigio codigo funcional durante esta auditoria. Este documento prepara las siguientes sesiones.

## Avance posterior

**Sesion 37 (2026-08-07):** corregidos A1, A4, A5, A6 (politica y ring-once), A15, A16 y A17. Implementadas F5+F6+F7 de D91. La validacion en Redmi fisico y Doze sigue pendiente; F8 overlay no se implementa salvo que F6+F7 fallen en hardware.

**Sesion 38 (2026-08-15):** corregidos A2, A3, A7, A8, A9, A10, A11, A12, A13, A14 y A18. Rama `fix/auditoria-fiabilidad` (mergeada a `dev`, commit `8299f24`, pusheada). Detalle: A2 (dobles tenis: strip `_doubles` + filtro modalidad en poller), A7 (agrupar por `(sport, league, event_id)`), A8 (error FCM permanente invalida `device.fcm_token`), A9 (buffer tenis 900s en `scheduler.buffer_for`), A10 (columna `message_type` + partial unique index), A11 (allowlist sport/liga + 404→fired), A12/A13/A14 (auto-refresh en `LaunchedEffect`, key inmutable, fútbol=1 card + `.take(MAX_FEATURED)`), A3 (arranque: device_id local síncrono, red en background), A18 (config dup, test NFL/tenis clock, black, docs). Railway desplegado + migracion A10 aplicada; smoke emulador OK (Home multi-sport + test-alarm end-to-end). Pendiente: smoke en hardware (Redmi/Doze/dos alarmas consecutivas).

## Hallazgos

### P0 - Fiabilidad directa de alarmas

#### A1. Cancelar una suscripcion no cancela su alarma local

**Estado:** corregido en Sesion 37.

**Evidencia:** `SubscriptionsViewModel.cancel()` elimina primero el elemento de `_state` y despues intenta encontrarlo en esa lista ya filtrada (`SubscriptionsViewModel.kt:89-101`). `current` siempre queda `null`, por lo que `AlarmScheduler.cancel()` no se ejecuta.

**Impacto:** el usuario ve "Alerta cancelada", el backend borra la suscripcion, pero una alarma ya programada puede sonar igualmente.

**Correccion propuesta:** capturar `current` antes del DELETE/cambio de estado y cancelar por `boutId` tras un DELETE exitoso. Anadir test que programe, cancele y compruebe tanto DataStore como `AlarmManager`.

#### A2. Las suscripciones de tenis dobles no pueden ser procesadas por el poller

**Estado:** corregido en Sesion 38.

**Evidencia:** la API usa un id sintetico `eventId_doubles` y solo lo convierte al id ESPN base dentro de `get_event_detail()` (`events.py:273-281`). Android persiste ese id sintetico al suscribirse (`EventDetailViewModel.kt:130-138`). El poller llama directamente a `provider.get_event_card(event_id)` sin quitar el sufijo (`poller.py:127-144`), y `EspnTennisProvider` construye la URL ESPN con el id recibido (`espn_tennis.py:375-378`).

**Impacto:** ESPN responde 404 y el poller salta todas las alertas de dobles. La UI permite crearlas, pero nunca se actualizan ni suenan.

**Correccion propuesta:** centralizar la conversion entre id publico y `provider_event_id`; usarla tanto en API como en poller. Mantener el id sintetico para presentacion/modalidad, pero consultar ESPN con el base y filtrar el card por `Doubles`. Test E2E de suscripcion `_doubles` hasta push `update`.

#### A3. El registro del dispositivo bloquea el hilo principal al arrancar

**Estado:** corregido en Sesion 38.

**Evidencia:** `MainActivity.onCreate()` ejecuta `runBlocking` y espera a `container.ensureRegistered()` (`MainActivity.kt:83-85`). Esa ruta puede esperar 3 s por Firebase y despues una llamada Retrofit con timeouts de 10/20 s (`AppContainer.kt:37-40,52-72`).

**Impacto:** arranque congelado y riesgo real de ANR cuando no hay red o Railway esta lento.

**Correccion propuesta:** lanzar el registro desde `lifecycleScope`/`repeatOnLifecycle` sin bloquear la primera composicion. Exponer estado de registro si una pantalla necesita auth; reintentar en background.

#### A4. DataStore puede perder alarmas por actualizaciones concurrentes

**Estado:** corregido en Sesion 37 con mutaciones dentro de una sola transaccion `DataStore.edit`.

**Evidencia:** `PendingAlarmStorage.put()` y `remove()` hacen read-modify-write en operaciones separadas (`PendingAlarm.kt:39-49`). FCM, `AlarmReceiver`, UI, cleanup y boot pueden ejecutarlas concurrentemente.

**Impacto:** dos pushes cercanos pueden leer el mismo mapa y la ultima escritura elimina silenciosamente la alarma que escribio la otra coroutine. Encaja con el sintoma historico "la siguiente alarma no suena".

**Correccion propuesta:** serializar mutaciones con `Mutex` o hacer una unica transformacion atomica dentro de `DataStore.edit`. Anadir test concurrente con dos `put` y con `put` + `remove`.

#### A5. Fallar al programar una alarma exacta se pierde sin recuperacion

**Estado:** corregido en Sesion 37: resultado explicito, persistencia del pendiente, notificacion accionable y restauracion al volver de Ajustes/reboot.

**Evidencia:** `AlarmScheduler.schedule()` llama directamente a `setAlarmClock()` sin comprobar permiso ni capturar `SecurityException` (`AlarmScheduler.kt:13-38`). `handleUpdate()` lo invoca en una `CoroutineScope` sin handler (`DespertarMeFirebaseService.kt:94-131`). El onboarding permite "Ahora no".

**Impacto:** si el permiso exacto falta o es revocado, el push se consume pero no queda alarma ni aviso visible al usuario.

**Correccion propuesta:** devolver un resultado explicito de scheduling, registrar fallo, mantener el `PendingAlarm` como no programado y mostrar notificacion accionable. Definir fallback compatible (`setAndAllowWhileIdle` o aviso inmediato) segun producto.

#### A6. El Bug B sigue sin una causa unica ni una prueba de regresion

**Estado:** mitigado en Sesion 37: politica pura con tests, lead 30 reprogramable, almacenamiento atomico y `fired` solo tras iniciar el tono. Falta smoke de dos alarmas consecutivas en hardware.

**Evidencia:** `scheduleFromAlarm()` aplica un suelo movil `now + 60 s` (`DespertarMeFirebaseService.kt:135-149`); lead >= 30 ignora toda reprogramacion posterior (`:124-129`); `AlarmReceiver` marca `fired=true` antes de confirmar que el servicio pudo arrancar (`AlarmReceiver.kt:35-68`). Ademas A4 puede perder otra alarma concurrente.

**Impacto:** una actualizacion tardia puede posponer el trigger, una alarma de 30 min nunca se corrige y un fallo al arrancar sonido consume para siempre el ring-once.

**Correccion propuesta:** no parchear una rama aislada. Extraer una politica pura de transiciones `Pending -> Scheduled -> Ringing -> Fired/Cancelled`, con tabla de casos y reloj inyectable. Cubrir dos alarmas consecutivas, multiples updates, update tardio, fallo del service y lead 0/5/15/30.

### P1 - Backend multi-sport y entrega FCM

#### A7. El poller mezcla ligas que compartan `sport + event_id`

**Estado:** corregido en Sesion 38.

**Evidencia:** agrupa por `(sport, event_id)` y toma la liga de la primera suscripcion (`poller.py:120-132`). La clave correcta del provider es `(sport, league)`.

**Impacto:** si ATP/WTA u otras ligas reutilizan un id, una suscripcion se procesa con el provider equivocado. Tambien vuelve no determinista el resultado segun el orden de BD.

**Correccion propuesta:** agrupar y cachear por `(sport, league, provider_event_id)`. Test con dos suscripciones de mismo id y ligas distintas.

#### A8. Un error FCM permanente en `update` sigue reintentandose cada ciclo

**Estado:** corregido en Sesion 38.

**Evidencia:** al fallar permanentemente, se escribe una marca Redis y se devuelve `True` (`poller.py:287-294`), pero el camino `update` no consulta `was_fired()` y tampoco cambia `sub.status` ni el device. Como no guarda `last_estimate`, el siguiente poll reenvia lo mismo.

**Impacto:** persiste el spam/consumo que D66 pretendia eliminar, especialmente con tokens restaurados o desregistrados.

**Correccion propuesta:** clasificar excepciones FCM por tipo, invalidar el token/device o cerrar todas suscripciones afectadas, y no contar un fallo como push enviado. Test de dos ciclos con `NotRegistered`.

#### A9. El buffer de tenis configurado nunca se usa

**Estado:** corregido en Sesion 38.

**Evidencia:** `buffer_intermatch_tennis_seconds=900` solo aparece en `config.py`. El dispatcher de `scheduler.py:120-133` contempla NBA/NFL y para tenis cae al buffer general MMA de 600 s.

**Impacto:** las estimaciones de tenis quedan 5 minutos antes de la decision D53/documentacion, afectando el momento de alarma.

**Correccion propuesta:** politica de buffer unica por deporte, con casos MMA, tenis, NBA, NFL y futbol. Tests parametrizados que lean settings reales.

#### A10. La auditoria de pushes pierde eventos dentro de la misma hora

**Estado:** corregido en Sesion 38.

**Evidencia:** UNIQUE de `alert_log` sigue siendo `(subscription_id, bout_id, fired_at_epoch_hour)` (`alert_log.py:24-27` y migracion `f7a0001:185-187`). No incluye `message_type`, aunque una misma suscripcion puede recibir varios `update` y despues `started` en una hora.

**Impacto:** `_log_alert()` hace rollback por duplicado y desaparecen filas validas de auditoria. La UI/historial no refleja todas las entregas.

**Correccion propuesta:** columna `message_type` real y clave idempotente acorde al mensaje; para `update`, incluir estimacion/version o no imponer unicidad horaria. Migracion y tests de `update -> update -> started`.

#### A11. La API acepta suscripciones a eventos/bouts inexistentes

**Estado:** corregido en Sesion 38.

**Evidencia:** `create_subscription()` valida lead contextual, pero no comprueba que `sport`, `league`, evento y bout existan ni que el match number coincida (`subscriptions.py:50-82`).

**Impacto:** filas activas imposibles de procesar permanecen indefinidamente y generan warnings cada minuto.

**Correccion propuesta:** validar enums/allowlist y pertenencia del bout al evento al crear, o marcar automaticamente `cancelled` tras 404 persistente con causa registrada.

### P1 - Lifecycle y UI Android

#### A12. Cada regreso a una pantalla crea otro auto-refresh infinito

**Estado:** corregido en Sesion 38.

**Evidencia:** cada `LaunchedEffect` llama a `startAutoRefresh()` (`MainActivity.kt:286-345`), pero ese metodo abre un nuevo job en `viewModelScope` y no conserva/cancela el anterior (`HomeViewModel.kt:144-151`, `CompetitionsViewModel.kt:104-111`, `EventDetailViewModel.kt:102-109`).

**Impacto:** tras navegar varias veces hay N loops cada 30 s, multiplicando llamadas, carreras y consumo de bateria/red incluso cuando la ruta ya no esta visible.

**Correccion propuesta:** un unico `autoRefreshJob` idempotente por VM y parada explicita, o mover el loop al `LaunchedEffect` ligado al lifecycle visible. Tests con scheduler virtual que prueben una sola llamada por tick.

#### A13. El refresh de detalle puede escribir datos de otro evento

**Estado:** corregido en Sesion 38.

**Evidencia:** `refreshSilently()` captura `eventId`, pero lee `currentSport/currentLeague` mutables al hacer la llamada y escribe sin verificar que la navegacion siga siendo la misma (`EventDetailViewModel.kt:111-119`). Los loops duplicados de A12 agravan la carrera.

**Impacto:** al cambiar rapido ATP/WTA/deporte, una respuesta antigua puede sobrescribir el evento actual.

**Correccion propuesta:** capturar una key inmutable `(eventId,sport,league)`, cancelar el job anterior y aplicar resultado solo si la key sigue vigente.

#### A14. Home ignora su limite y refresca demasiados detalles

**Estado:** corregido en Sesion 38.

**Evidencia:** `MAX_FEATURED=6` no se usa (`HomeViewModel.kt:233-250`). La seleccion devuelve uno por `sport+league`: actualmente hasta 12 cards. Cada carga y cada 30 s hace todos los listados y luego un detalle por card.

**Impacto:** carga innecesaria en movil, Railway y ESPN; aumenta el riesgo de OOM/503 que ya aparecio anteriormente.

**Correccion propuesta:** aplicar el limite despues de garantizar la politica de destacados acordada, deduplicar el pipeline `load/refresh`, y medir requests por ciclo. Considerar cache corta para detalles.

#### A15. `ACTION_STOP` deja una notificacion FSI huerfana

**Estado:** corregido en Sesion 37.

**Evidencia:** `AlarmService.ACTION_STOP` solo retira su foreground notification (`AlarmService.kt:41-45`). No cancela `AlarmReceiver.FULLSCREEN_NOTIFICATION_ID`, tal como ya recoge D91/F5.

**Impacto:** el sonido para, pero la notificacion de alarma puede quedar fija y volver a abrir la pantalla.

**Correccion propuesta:** una unica operacion `stopAlarm()` que pare audio, libere wakelock, cancele ambas notificaciones y actualice almacenamiento.

#### A16. Dos `ACTION_START` pueden dejar un ringtone imposible de parar

**Estado:** corregido en Sesion 37; cada start detiene el playback anterior y STOP restaura el volumen previo.

**Evidencia:** cada start crea un nuevo `Ringtone` y sobrescribe la referencia sin parar el anterior (`AlarmService.kt:67-91`). `onDestroy()` solo detiene la ultima referencia.

**Impacto:** dos alarmas cercanas o un `started` mientras otra suena pueden dejar audio antiguo reproduciendose.

**Correccion propuesta:** hacer el service idempotente: detener/release previo antes de reproducir, decidir politica de cola/reemplazo y probar dos starts + un stop.

#### A17. `BootReceiver` lanza trabajo async sin `goAsync()`

**Estado:** corregido en Sesion 37.

**Evidencia:** abre una coroutine y retorna inmediatamente (`BootReceiver.kt:14-29`). Android puede matar el proceso al terminar `onReceive`.

**Impacto:** tras reinicio, parte o todas las alarmas pueden no reprogramarse.

**Correccion propuesta:** `val pendingResult = goAsync()` y `finish()` en `finally`, o WorkManager si el trabajo crece. Test Robolectric del ciclo de receiver.

### P2 - Seguridad, calidad y deuda operativa

#### A18. Gates y documentacion no representan el estado real

**Estado:** corregido en Sesion 38 (config dup, test NFL/tenis clock, black, docs contexto/arquitectura/README). Los tests Android utiles ya existen (AlarmTriggerPolicyTest, HomeViewModelTest). El riesgo de `POST /api/devices` (X-Device-Id como identidad) se acepta para dogfooding.

- `pytest`: falla un test NFL dependiente del reloj; el fixture ya quedo en el pasado (`test_espn_nfl.py:52-64`).
- `mypy`: falla por el validador `_normalize_database_url` duplicado (`config.py:75-95`).
- `black --check`: reformatearia `events.py`, `espn_nfl.py`, `scheduler.py` y `test_espn_nfl.py`.
- Android no tiene tests utiles: solo `ExampleUnitTest.addition_isCorrect()`.
- `README.md`, `contexto.md` y `arquitectura.md` aun describen User/Twilio/web y no Device/FCM/Kotlin/multi-sport.
- `POST /api/devices` permite reactivar y sustituir el token de cualquier device id conocido; `X-Device-Id` es identidad, no autenticacion. Para dogfooding personal es riesgo aceptado, pero no para publicacion.

## Orden de ejecucion recomendado

### Sesion 1 - Red de seguridad y P0 de cancelacion

- Corregir A18 minimo: validador duplicado, formato y test NFL con reloj/min_date fijo.
- Introducir tests Android reales para politica de trigger y repositorio de alarmas.
- Corregir A1 y A4.
- Verificar dos alarmas almacenadas, cancelar una y confirmar que la otra permanece.

### Sesion 2 - Poller multi-sport

- Corregir A2, A7 y A9 como una unidad coherente de identidad/provider/politica por deporte.
- Anadir fixtures E2E para ATP, WTA y dobles con ids potencialmente solapados.
- Corregir A8 y A10 con migracion de auditoria.

### Sesion 3 - Maquina de estados de alarma

- Resolver A5, A6, A15, A16 y A17.
- Extraer politica pura de scheduling y estado; mantener Android framework en adaptadores finos.
- Implementar F5+F6 de D91 y probar en Pixel/emulador antes del Redmi.

### Sesion 4 - Lifecycle y rendimiento

- Corregir A3, A12, A13 y A14.
- Medir numero de requests durante 5 minutos navegando Home/Buscar/Detalle.
- Confirmar que al abandonar una pantalla cesa su polling.

### Sesion 5 - Hardware y operacion

- Matriz en Redmi bloqueado/desbloqueado, app foreground/background/cerrada.
- Dos alarmas consecutivas y dos simultaneas.
- Revocar exact alarms/FSI/notificaciones y validar degradacion visible.
- Forzar Doze y reinicio.
- Suscripcion real MMA, tenis singles/dobles, NBA/NFL Q2-Q4.
- Si F6 no rompe MIUI, ejecutar F7; usar F8 solo como fallback final.

## Criterios de cierre

- Cancelar una suscripcion elimina alarma del backend, DataStore y AlarmManager.
- Dos updates concurrentes nunca pierden otra alarma.
- Dobles genera al menos un `update` real desde el poller.
- Un token FCM invalido se procesa una sola vez y queda recuperable al registrar token nuevo.
- Solo existe un auto-refresh por pantalla visible.
- El arranque pinta UI sin esperar red.
- Dos `ACTION_START` seguidos se detienen completamente con un solo STOP.
- Reboot y Doze conservan alarmas futuras.
- Redmi muestra UI accionable sobre lockscreen o mediante fallback aprobado.
- `ruff`, `black --check`, `mypy`, `pytest`, `assembleDebug` y tests Android quedan verdes.

## Comandos de verificacion

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m black --check -W 1 src tests
.\.venv\Scripts\python.exe -m mypy src/app
.\.venv\Scripts\python.exe -m pytest
cd mobile-kotlin
.\gradlew.bat testDebugUnitTest assembleDebug
```

Los smokes de Doze, reboot, FSI y MIUI requieren emulador/dispositivo y no deben darse por cerrados solo porque compile la APK.
