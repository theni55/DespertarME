# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

---

## Última sesión

**Fecha:** 2026-07-16 · **Sesión 14 — Decisión: pivot a Kotlin nativo puro (sin Expo/RN) para la app Android. Plan de ejecución consolidado (ver "Próximos pasos").**

**Contexto:** el owner preguntó si, teniendo Android Studio, se podía quitar Expo para simplificar el desarrollo. Análisis: la funcionalidad crítica del MVP (AlarmScheduler, AlarmService, AlarmActivity, bypass DnD, FCM) es Kotlin sí o sí — Expo solo cubría la capa de pantallas a cambio de mantener dos runtimes (JS + nativo), el bridge, Metro, Node y EAS (que ya dio problemas: build ERRORED por lock, colas ~2h). **Decisión del owner: quitar Expo e ir a Kotlin nativo + Jetpack Compose.** Coste asumido: iOS (Fase 7d, post-MVP) será rewrite SwiftUI en vez de reutilizar pantallas TS (la alarma iOS requería módulo Swift/AlarmKit nativo de todos modos).

⚠️ **Pendiente de registrar D43** en `decisiones.md` (supersede el stack RN+Expo de D37; no editar D37) y de reescribir §7b/7c en `fases.md` — primer paso de la próxima sesión de ejecución.

**Hallazgo de entorno (verificado en la máquina del owner):** el setup de emulador de las sesiones 10-11 se hizo en la máquina del compañero. En este PC NO hay Android Studio, ni SDK, ni adb, ni AVD; Java es 1.8 (insuficiente, Android Studio trae JDK 17 embebido); hipervisor activo ✅; Node presente (dejará de hacer falta al quitar Expo); `mobile/node_modules` ausente (irrelevante tras el pivot); backend local listo (venv + `.env` efectivo apunta a SQLite).

**Verificación backend para testing sin deps externas:** arranca y sirve `GET /api/events` y `GET /api/events/{id}` **sin Redis** (caché con bypass try/except en `events.py:99-103`, resolver degradado a L1 en memoria) y **sin Firebase** (cae a `DummyNotifier`, `notifiers/__init__.py:27-45`). El poller sí necesita Redis para disparar alertas (idempotencia en `engine/state.py`), pero sin él la API sigue viva — se difiere al tramo FCM.

---

## Sesión 13 (anterior)

**Fecha:** 2026-07-16 · **Sesión 13 — Code review de Fase 7a + 4 fixes bloqueantes ✅. Plan hacia el MVP Android consolidado.**

**Contexto:** review multi-eje (skill `code-review-and-quality`) del commit `6470b24` (Fase 7a, ~2.400 líneas) mergeado a `dev` por el compañero. Veredicto: diseño sólido (idempotencia en profundidad, fixes E2–E8 bien razonados, suite reescrita de calidad) pero con 1 bug crítico + 2 required + 1 de higiene, todos arreglados en esta sesión.

**Fixes aplicados (con test de regresión cada uno):**

1. **[Critical] FCM roto en producción** (`notifiers/fcm.py`): la app Firebase se inicializa con nombre propio (`despertarme-fcm`) pero `messaging.send(message, False)` sin `app=` resuelve contra la app *default* (inexistente) → `ValueError` en **cada** envío real. Los tests no lo veían porque mockean `messaging` entero. Fix: `send(message, False, self._app)` + `get_app(name="despertarme-fcm")` para reutilizar la app nombrada al re-instanciar. Assert de regresión en `test_fcm_notifier_send_returns_message_id_on_success`.
2. **[Required] Caché de events ignoraba `include_past_hours`** (`api/routes/events.py`): clave fija `events:upcoming:ufc` → una query con cutoff distinto servía/poblaba la lista de otra durante el TTL. Fix: solo la query default (`include_past_hours == 0`, la que usa la app) lee/escribe caché. Test nuevo `test_list_events_cache_only_applies_to_default_query` (fakeredis inyectado en los singletons del router).
3. **[Required] Normalización asimétrica del `device_id`**: el registro hace `.strip().lower()` (`schemas.py`) pero la auth solo `.strip()` (`security/device.py`) → un cliente con UUID en mayúsculas se registraba bien y luego recibía 401 siempre. Fix: misma normalización en `get_current_device`. Test nuevo `test_device_header_is_case_insensitive`.
4. **[Higiene] `inst_user_settings.tmp` eliminado**: temporal del instalador de Android Studio (con rutas locales del compañero) commiteado por accidente en `f2ad55e`. Borrado + `*.tmp` en `.gitignore`.

**Hallazgos de la review NO arreglados (deuda consciente, para 7b/7c):**

- **alert_log UNIQUE traga auditoría**: `(subscription_id, bout_id, fired_at_epoch_hour)` era de la era fire-once; con D40 puede haber varios `update` (o `update`+`started`) del mismo sub/bout en la misma hora → el 2º insert choca con IntegrityError y el push queda enviado pero sin auditar. Propuesta: añadir `message_type` al UNIQUE (migración pequeña).
- **`POST /api/devices` es upsert sin auth con ID de cliente**: quien conozca un `device_id` puede sobrescribir su `fcm_token`. Aceptable MVP (UUID opaco), pero sin rate-limiting y `min_length=32` admite no-UUIDs. Propuesta: validar UUID v4 estricto.
- Nits: `attempts` en `_log_alert` registra siempre el máximo; `session` inyectada sin uso en events; `downgrade()` de la migración recrearía ENUMs sin valores en PG (best-effort, irrelevante); `get_transition` posiblemente dead code.

**Verificación:** 80 tests verdes (78 + 2 nuevos), ruff/black/mypy limpios.

---

## Próximos pasos (plan aprobado Sesión 14 — app Android Kotlin nativo, deps externas al mínimo y al final)

Requisito de instalación: **solo Android Studio** (trae SDK, emulador, adb, JDK 17, Kotlin, Gradle). Sin Node, sin Metro, sin EAS, sin Docker hasta el tramo FCM.

### Paso 1 — Preparación (1 sesión)

1. Instalar **Android Studio** (`winget install Google.AndroidStudio`) + crear AVD Google APIs **API 34** (D41; hipervisor ya activo en la máquina del owner).
2. Registrar **D43** en `decisiones.md`: pivot a Kotlin nativo + Jetpack Compose, supersede el stack RN+Expo de D37. Justificación: MVP Android-only, código crítico ya nativo, menos capas de fallo (un lenguaje, una toolchain), FCM con SDK `firebase-messaging` directo, builds locales sin EAS. Coste: iOS 7d será rewrite SwiftUI.
3. Reescribir **§7b/7c en `fases.md`**: Compose + Navigation + ViewModel, Retrofit/Ktor, DataStore para `device_id`, `firebase-messaging` directo, `./gradlew assembleRelease` local.
4. **Scaffold Kotlin** reemplazando el spike Expo en `mobile/` (el spike queda en historial git): paquete `com.despertarme.app`, minSdk 26 / target 34, portar `AlarmService.kt` casi tal cual; descartar `App.tsx`, `AlarmModule.kt`, `AlarmPackage.kt`, `package.json` y config Expo.
5. **Backend local**: `alembic upgrade head` + `uvicorn` con SQLite (ya configurado, sin Docker). El emulador alcanza el host en `http://10.0.2.2:8000`.
6. **Smoke en emulador**: app arranca + alarma de prueba suena → primer checkbox de 7b.

### Paso 2 — Fase 7b core (camino crítico, ~2-3 sesiones)

1. **`AlarmScheduler`** (`AlarmManager.setAlarmClock()` a `estimated_start − lead`) + **verify-then-ring** (fetch `GET /api/events/{id}` al sonar → sonar/reprogramar/silenciar). Refactor `AlarmService`: `res/raw/alarm.ogg` custom + `AlarmActivity` full-screen. Permisos: `USE_EXACT_ALARM`, `USE_FULL_SCREEN_INTENT`, `RECEIVE_BOOT_COMPLETED`.
2. **Todo probable en emulador SIN FCM ni Redis** (gracias a D40: la alarma local es la fuente de verdad). Doze: `adb shell dumpsys deviceidle force-idle`.

### Paso 3 — Pantallas Compose (~1-2 sesiones)

Home (hero McGregor D42 + "Avísame") / Eventos / EventDetail (selector lead 5/10/15/30/60) / Mis Alertas / Ajustes (test-alarm) / AlarmScreen. Tokens: Inter, `#E50914`, `#0A0A0A`. `device_id` UUID en DataStore + `POST /api/devices`. Solo necesita emulador + backend SQLite.

### Paso 4 — Tramo FCM (aquí entran las deps externas)

1. **Firebase** (manual owner, ~30 min): proyecto + service account JSON → `FCM_CREDENTIALS_JSON` (backend) + `google-services.json` → `mobile/app/`.
2. **Redis** (`docker compose up -d`, ya definido en el repo): desbloquea el poller (idempotencia).
3. Cliente FCM nativo (`firebase-messaging`): `update` → reprogramar alarma; `started`/`cancelled` → notificación informativa.

### Paso 5 — Validación final + deploy (Fase 7c)

Móvil físico (bypass DnD real + quirks OEM) → Railway (PG + Redis + `FCM_CREDENTIALS_JSON`) → APK release local (`./gradlew assembleRelease`) → smoke end-to-end.

### Paso 6 — Deuda de la review Sesión 13 (oportunista, no bloquea)

`message_type` en el UNIQUE de alert_log · UUID v4 estricto en `DeviceCreate` · nits listados en Sesión 13. Pedir al compañero PRs más pequeñas en 7b.

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
| Fase 7 — App móvil | 🔶 **En curso** — Spike ✅, Fase 7a (backend Device/FCM) ✅ + review con 4 fixes ✅. **Sesión 14: pivot a Kotlin nativo puro (sin Expo, D43 pendiente de registrar).** Próximo: instalar Android Studio + scaffold Kotlin + AlarmScheduler D40. |

Detalle de checkboxes en `fases.md`.

---

## Ramas

- `dev` (activa): backend API-only + `mobile/` spike + memoria viva. Sesión 14 (plan pivot Kotlin nativo) en handoff; el scaffold Kotlin reemplazará el spike Expo en la próxima sesión.
- `main`: sincronizada con `dev` hasta Fase MVP-launch (el pivot 7a aún no está en main).
- `web` (congelada en `dcf62f8`): landing, admin web, `/app/*`. `git checkout web` para consultarla.

---

## Cómo levantar el backend en local

```powershell
.\.venv\Scripts\Activate.ps1
# .env: DATABASE_URL=sqlite+aiosqlite:///./avisador.db
alembic upgrade head
uvicorn app.main:app --reload
```

- `http://localhost:8000/health` → `{"status":"ok"}`
- `http://localhost:8000/docs` → Swagger UI (9 endpoints: devices, events, subscriptions, alerts, health)

**La web solo existe en la rama `web`.**

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
