# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

---

## Última sesión

**Fecha:** 2026-07-15 · **Sesión 9 — Análisis del plan de migración + codebase review + nuevas decisiones D40/D41.**

**Contexto:** el owner pidió revisar el plan de migración web→móvil (Fase 7) y la codebase para evaluar su solidez, y planteó la idea de crear alarmas locales en el dispositivo en vez de depender de FCM como timbre. La sesión fue exclusivamente de análisis y actualización de memorias — **cero cambios de código**.

**Decisiones nuevas (Sesión 9):**

- **D40 — Arquitectura de alarma híbrida**: `setAlarmClock` en Android / AlarmKit en iOS 26+ (verificado contra doc Apple WWDC25 — no requiere Critical Alert Entitlement). FCM pasa de "ring now" a "actualizador de estimación". Verify-then-ring: la alarma local consulta al backend antes de sonar (self-healing).
- **D41 — Validación emulador-primero**: Android Studio + emulador API 34 se adelanta de Fase 7b al spike. El emulador cubre validación de código (crash E1, sonido, DnD, Doze); el móvil físico queda como confirmación final de quirks OEM.

**Hallazgos principales de la codebase review:**

- **Crash del spike (E1) — diagnóstico casi seguro**: falta `android.permission.FOREGROUND_SERVICE` en `AndroidManifest.xml` y `app.json`. `SecurityException` en `startForeground` (API 28+), fuera del try/catch del bridge → la app muere sin mensaje JS. Fix de 1 línea + 3 defensivos (null-check `getRingtone`, quitar prompt Settings del flujo `startAlarm`, guard API 28 en `isLooping`).
- **E2 — Estimación `post` se desliza al infinito** (`estimator.py:111-118`): `start = now + buffer` se recalcula en cada poll → `lead < 5` nunca dispara. Con D40, la alarma local se reprogramaría cada vez hacia delante. Fix: anclar a la primera observación de la transición.
- **E3 — Poller nunca mira el combate objetivo** (`poller.py:104-122`): puede disparar "empieza en 5 min" horas tarde. Falta guard + mensajes `started`/`cancelled`.
- **E4 — `previous_bout_id` congelado por el cliente** (`subscriptions.py:43`): reordenaciones de UFC producen estimaciones incoherentes. Derivarlo server-side.
- **E5 — CB se abre con 404**: DoS trivial cuando exista `GET /api/events/{id}` público.
- **E6 — `fired_at_hour = now.hour`** colisiona entre días + falta UNIQUE `(device_id, bout_id)`.
- **E7 — Retries de voz bloquean el poll** (36 s sleep); no aptos para FCM.
- **E8 — Sin caché de card por ciclo**: N subs = N fetches idénticos a ESPN por minuto.
- **5 trampas de migración en Fase 7a**: FKs de `sport_subscriptions`/`event_subscriptions`, ENUM `user_role` huérfano en PG, no naming convention en Base, `new_uuid` en `auth/`, `model_validator` de `jwt_secret`.
- **Fase 7b listaba `FOREGROUND_SERVICE_DATA_SYNC`** — tipo erróneo; el spike usa `mediaPlayback`, correcto.
- **Fase 7d obsoleta**: la premisa "Critical Alert Entitlement" ya no aplica — AlarmKit (iOS 26, WWDC25) es la ruta oficial.

**Memorias actualizadas en esta sesión:** `decisiones.md` (D40/D41 + pendientes), `fases.md` (Spike, 7a ampliada, 7b, 7d), `handoff.md` (este fichero), `bitacora.md` (entrada Sesión 9). Commit único en `dev`.

---

## Próximos pasos (ordenados para el continuador)

### Paso 1 — Desbloquear el spike (lo más urgente, ventana de hardware del owner)

1. **Instalar Android Studio + emulador API 34 Google APIs** (~5-8 GB disco + JDK 17 + virtualización activada en Windows).
2. **Reproducir el crash** en emulador con `npx expo run:android` + `logcat`:
   - Confirmar (o refutar) que es `SecurityException` por falta de `FOREGROUND_SERVICE`.
   - Si es otra cosa: analizar el stack trace real y ajustar.
3. **Aplicar fix + defensivos**:
   - `AndroidManifest.xml` + `app.json`: añadir `<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>`.
   - `AlarmService.kt:45`: null-check en `getRingtone()` con callback de error al JS.
   - `AlarmModule.kt:46-48`: mover `promptPolicyAccess()` fuera de `startAlarm` (innecesario — bitacora:410).
   - `AlarmService.kt:50`: guard `Build.VERSION.SDK_INT >= 28` para `isLooping`.
4. **Validar en emulador**: DnD activado → "Probar alarma" suena → "Parar" limpia → logcat sin errores.
5. **`git commit` + `git push`** a `dev`.
6. **Build EAS #3** (`npx eas build --platform android --profile development`) → instalar APK en el móvil Android 14 del owner → probar con DnD/silencio.
7. Si falla en el device pero no en emulador: documentar marca/modelo y stack trace para abordar el quirk OEM concreto.

### Paso 2 — Fase 7a (backend)

Ver checklist completo en `fases.md` §Fase 7a. Prioridades:
1. Las 5 trampas de migración primero (antes de borrar nada).
2. Fixes E2/E3/E4/E6 en el Poller/Estimador durante el refactor.
3. Contrato FCM D40 (push on-change).
4. Tests (~31 sobreviven intactos; reescribir poller/api/notifiers; añadir tests para E2/E3/E4).

### Paso 3 — Fase 7b (app Android v1)

Ver checklist en `fases.md` §Fase 7b. El `AlarmScheduler` (D40) es la pieza nueva central; Android Studio ya debería estar instalado de D41.

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
| Fase 7 — App móvil | 🔶 **En curso** — Spike: build OK, crash en device (E1 diagnosticado); plan 7a/7b/7d actualizado con D40/D41 + fixes de codebase review |

Detalle de checkboxes en `fases.md`.

---

## Ramas

- `dev` (activa): API-only + `mobile/` spike + memoria viva.
- `main`: sincronizada con `dev`.
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
- `http://localhost:8000/docs` → Swagger UI

**La web solo existe en la rama `web`**.

---

## Comandos quick-start

```powershell
.\.venv\Scripts\Activate.ps1            # activar venv
alembic upgrade head                    # aplicar migraciones (SQLite)
uvicorn app.main:app --reload            # servidor dev (API-only)
pytest -v                                # tests (64 verdes en dev)
python scripts/probe_espn.py              # smoke ESPN en vivo
ruff check src tests                      # lint
black --check src tests scripts           # formato
mypy src/app                              # type check
python scripts/gen_memoria_index.py       # regenerar índice en AGENTS.md
```
