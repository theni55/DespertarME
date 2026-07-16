# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

---

## Última sesión

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

## Próximos pasos (plan MVP Android, ordenado por dependencia)

El camino crítico es la **Fase 7b**; todo lo demás son horas, no días.

### Paso 0 — Firebase (manual del owner, ~30 min, desbloquea el smoke real)

1. Crear proyecto Firebase.
2. Service account key JSON → env-var `FCM_CREDENTIALS_JSON` (backend; sin ella cae a `DummyNotifier`).
3. `google-services.json` → `mobile/android/app/` (app).

### Paso 1 — Fase 7b (app Android v1, D40/D41 — el grueso, ~3-5 sesiones)

Ver checklist completo en `fases.md` §Fase 7b. Hoy `mobile/` solo tiene el spike (1 pantalla, sonido). Prioridad dentro de 7b: **el `AlarmScheduler` + verify-then-ring es lo que valida el MVP; las pantallas son trabajo mecánico.**

1. **Nativo (Kotlin):** `AlarmScheduler` con `AlarmManager.setAlarmClock()` a `estimated_start − lead` + verify-then-ring (fetch `GET /api/events/{id}` al sonar → sonar/reprogramar/silenciar). Refactor `AlarmService` del spike: `res/raw/alarm.ogg` custom + `AlarmActivity` full-screen. Permisos nuevos: `USE_EXACT_ALARM`, `USE_FULL_SCREEN_INTENT`, `RECEIVE_BOOT_COMPLETED`.
2. **JS/TS:** cliente FCM (`@reactnative-firebase/messaging`; background `update` → reprogramar alarma, NO arrancar service), `device_id` UUID en `expo-secure-store` + `POST /api/devices`, TanStack Query.
3. **Pantallas (Expo Router Tabs):** Home (hero McGregor D42 + "Avísame"), Eventos, EventDetail (selector lead 5/10/15/30/60), Mis Alertas, Ajustes (test-alarm), AlarmScreen modal. Tokens: Inter, `#E50914`, `#0A0A0A`.
4. **Validación:** emulador (flujo completo + Doze `dumpsys deviceidle force-idle`) → móvil físico (bypass DnD + quirks OEM).

### Paso 2 — Fase 7c (deploy + smoke real, ~1 sesión)

Backend en Railway (PG + Redis + `FCM_CREDENTIALS_JSON`). Build EAS → APK. Smoke end-to-end: crear alerta → poller detecta fin del previo → push `update` → alarma local suena con DnD activo.

### Paso 3 — Deuda de la review (oportunista, no bloquea)

`message_type` en el UNIQUE de alert_log · UUID v4 estricto en `DeviceCreate` · nits listados arriba. Pedir al compañero PRs más pequeñas en 7b (las "tandas" son fronteras naturales de commit).

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
| Fase 7 — App móvil | 🔶 **En curso** — Spike ✅, Fase 7a (backend Device/FCM) ✅ **+ review con 4 fixes aplicados** ✅. Próximo: Firebase (owner) + Fase 7b (app Android con AlarmScheduler D40). |

Detalle de checkboxes en `fases.md`.

---

## Ramas

- `dev` (activa): backend API-only + `mobile/` spike + memoria viva. Sesión 13 (review + fixes) commiteada y pusheada.
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
