# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

---

## Última sesión

**Fecha:** 2026-07-15 · **Sesión 11 — Spike validado en emulador: fix E1 + bypass DnD funcionando ✅.**

**Contexto:** tras aprobar el diálogo UAC de Hyper-V (Sesión 10), el owner activó VT-x en la BIOS (ASUS ROG STRIX Z370-F → Advanced → CPU Configuration → Intel Virtualization Technology → Enabled). WHPX quedó operativo (`emulator -accel-check` = "WHPX is installed and usable"). El emulador arrancó, la app compiló en local con Gradle, y el fix E1 fue validado end-to-end.

**Logros de la sesión:**

- **Variables de entorno permanentes** fijadas en perfil User: `JAVA_HOME`, `ANDROID_HOME`, `PATH` (emulator + platform-tools + cmdline-tools).
- **Emulador arrancado** (`pixel_6_api34`, WHPX, GPU RTX 2080): boot en ~75 s primer intento, ~32 s segundo. Snapshot `default_boot` guardado.
- **Build local exitoso** (`gradlew assembleDebug`, 2m 29s): APK debug generado en `mobile/android/app/build/outputs/apk/debug/app-debug.apk` (~129 MB). Hito: primera compilación Kotlin del spike en local confirmada limpia (solo warnings de deprecación, sin errores).
- **APK instalado en emulador** vía `adb install -r` → "Success".
- **Fix E1 VALIDADO** ✅: "Probar alarma" → app NO crashea, `AlarmService` foreground activo (`isForeground=true`, `category=alarm`, `mediaPlayback`), logcat limpio sin `AndroidRuntime`. El crash de la Sesión 8 estaba causado por falta del permiso `FOREGROUND_SERVICE` → `SecurityException` en `startForeground` (API 28+) → muerte del proceso fuera del try/catch del bridge JS-Native.
- **Bypass DnD VALIDADO** ✅: con DnD "Alarms only" (`zen_mode=1`, `cmd notification set_dnd priority`) + volumen `STREAM_ALARM` al máximo, el ringtone `TYPE_ALARM` con `USAGE_ALARM` suena (logcat: `AudioTrack: stop(16): called with 91283 frames delivered`, MediaPlayer `state:started`). **No** suena con DnD "Total silence" (`zen_mode=2`) — AOSP mutes `STREAM_ALARM` en ese modo. Hallazgo técnico: `setBypassDnd(true)` del canal sale como `mBypassDnd=false` en dumpsys del emulador but el ringtone suena igual (el bypass del canal afecta a la notificación visual, no al stream de audio).
- **Parada limpia** ✅: "Parar" → UI "Service: stopped", `dumpsys activity services` sin ServiceRecord, player released, notificación retirada, logcat limpio.
- **Build EAS nueva lanzada** (build ID `fa4366ee`, con fixes E1 incluidos, commit `0d7dff9`). En cola free tier ~1-2h. URL: https://expo.dev/accounts/theni55/projects/despertarme-spike/builds/fa4366ee-ed46-4bfa-9adb-6b8158b88232

**Hallazgos técnicos importantes para el continuador:**

1. **`gradlew assembleDebug` directo NO empaqueta el JS bundle** dentro del APK. La app abre con Red Box "Unable to load script". Fix: arrancar Metro (`npx expo start`) + `adb reverse tcp:8081 tcp:8081` → la app descarga el JS en vivo del Metro en el host. Para builds standalone (sin Metro), empaquetar el bundle con `react-native bundle` (requiere `@react-native-community/cli`).
2. **DnD "Total silence"** (`set_dnd on` → `zen_mode=2`) mutes `STREAM_ALARM` en AOSP puro. Usar `set_dnd priority` (`zen_mode=1`, "Alarms only") para validar bypass. En dispositivos físicos reales, los OEM (Samsung/Xiaomi) suelen excluir `STREAM_ALARM` del mute incluso en Total silence.
3. **`cmd notification set dnd on`** no funciona (comando correcto: `cmd notification set_dnd on`).
4. **`ACCESS_NOTIFICATION_POLICY`** no es concedible vía `adb pm grant` (no es runtime permission). Pero el bypass DnD del canal `IMPORTANCE_HIGH` + `setBypassDnd(true)` + `USAGE_ALARM` funciona sin necesitarlo (bitacora:410 confirmado en emulador).
5. **`media volume --stream 4 --set 7`** no existe en AOSP. Subir volumen con `input keyevent 24` (VOLUME_UP) repetido.

**Memorias actualizadas:** `handoff.md` (esta entrada), `bitacora.md` (Sesión 11), `fases.md` (Spike completado ✅). Commit + push a `dev` pendiente.

---

## Próximos pasos (ordenados para el continuador)

### Paso 1 — Confirmación en móvil físico (opcional, no bloqueante)

**Estado:** spike validado en emulador ✅. La build EAS `fa4366ee` (con fixes E1) está en cola — cuando termine, descargar el APK e instalar en el móvil Android 14 físico del owner para confirmar OEM quirks (Xiaomi/Samsung/etc.) del bypass DnD. El emulador AOSP ya confirmó el flujo estándar; el móvil físico es la confirmación final para quirks de fabricante. No bloquea el avance a Fase 7a.

URL build EAS: https://expo.dev/accounts/theni55/projects/despertarme-spike/builds/fa4366ee-ed46-4bfa-9adb-6b8158b88232

### Paso 2 — Fase 7a (backend)

Ver checklist completo en `fases.md` §Fase 7a. Prioridades:
1. Las 5 trampas de migración primero (antes de borrar nada).
2. Fixes E2/E3/E4/E6 en el Poller/Estimador durante el refactor.
3. Contrato FCM D40 (push on-change).
4. Tests (~31 sobreviven intactos; reescribir poller/api/notifiers; añadir tests para E2/E3/E4).

### Paso 3 — Fase 7b (app Android v1)

Ver checklist en `fases.md` §Fase 7b. El `AlarmScheduler` (D40) es la pieza nueva central; Android SDK ya instalado (JDK 17 + SDK 34) y emulador funcionando (WHPX). Iteración local confirmada viable (~2m 29s build + Metro + `adb reverse`).

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
| Fase 7 — App móvil | 🔶 **En curso** — Spike **validado** ✅ (fix E1 + bypass DnD funcionando en emulador). Build EAS `fa4366ee` en cola. Próximo: Fase 7a (backend device model + FCM). |

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
