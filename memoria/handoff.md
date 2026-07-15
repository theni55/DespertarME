# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

---

## Última sesión

**Fecha:** 2026-07-15 · **Sesión 10 — Fix E1 + setup Android SDK local + activación Hyper-V + build EAS #3 en vuelo.**

**Contexto:** el continuador ejecutó el Paso 1 del handoff de la Sesión 9. Se aplicaron los 4 fixes del crash E1, se instaló el Android SDK completo (JDK 17 + cmdline-tools + platform-tools + emulator + system-image API 34 + build-tools) mediante descargas portable (sin winget/admin), se disparó la activación de Hyper-V vía elevación UAC, y se lanzó build EAS #3 en paralelo como red de seguridad.

**Logros de la sesión:**

- **Fix E1 aplicado y commiteado** (`e896b88` en `dev`): 4 archivos modificados:
  1. `AndroidManifest.xml` + `app.json`: añadido `FOREGROUND_SERVICE` (el permiso genérico, no solo el specific `_MEDIA_PLAYBACK`).
  2. `AlarmModule.kt`: eliminada llamada a `promptPolicyAccess()` de `startAlarm` (innecesaria, manda la app a Settings antes del service).
  3. `AlarmService.kt`: null-check en `getRingtone()` (`?: return` evita NPE) + guard `Build.VERSION.SDK_INT >= 28` para `isLooping`.
  - TypeScript compila limpio (`tsc --noEmit`).
- **Android SDK instalado (portable, sin admin):**
  - JDK 17 (Temurin portable) en `%LOCALAPPDATA%\jdk-17\jdk-17.0.19+10`
  - Android SDK en `%LOCALAPPDATA%\Android\Sdk`: platform-tools, platforms;android-34, system-images;android-34;google_apis;x86_64, emulator, build-tools;34.0.0, cmdline-tools (layout `latest/`).
  - AVD `pixel_6_api34` creado con `avdmanager` (imagen Google APIs x86_64).
- **Hyper-V disparado** vía `Start-Process -Verb RunAs` (diálogo UAC pendiente de aprobación por el owner).
- **Build EAS #3 lanzada** (build ID `f486f8c5`, en cola free tier ~1-2h). URL: https://expo.dev/accounts/theni55/projects/despertarme-spike/builds/f486f8c5-d956-4ce9-ab79-2ed12a39a236
- **Explicación de los 3 caminos de testing** al owner: Camino A (emulador local, ~5 min/build), Camino B (móvil físico + build local vía Gradle, sin EAS), Camino C (EAS cloud build, lento pero sin dependencias locales). El owner eligió Camino A (emulador).

**Bloqueador actual:** el emulador requiere aceleración hardware (Hyper-V o WHPX). La UAC se disparó pero el PC necesita reinicio para activar Hyper-V. Pendiente: que el owner apruebe el diálogo UAC, reinicie el PC, y el continuador verifique `emulator -accel-check` en la próxima sesión.

**Memorias actualizadas:** `handoff.md` (esta entrada), `bitacora.md` (Sesión 10). Commit + push a `dev`.

---

## Próximos pasos (ordenados para el continuador)

### Paso 1 — Completar validación del spike (emulador o EAS)

**Estado:** fix E1 commiteado + build EAS #3 en vuelo + Hyper-V pendiente de reinicio. El continuador retoma así:

1. **Verificar estado de la build EAS #3**: si terminó, descargar e instalar APK en el móvil Android 14 del owner. Probar DnD → "Probar alarma" → ¿suena sin crash? → "Parar". Si crash persiste → `adb logcat` (platform-tools ya instalado).
2. **Verificar Hyper-V**: si ya se aprobó UAC + reinicio → ejecutar `$env:ANDROID_HOME\emulator\emulator.exe -accel-check` para confirmar aceleración activa.
3. **Si Hyper-V funciona → Camino A (emulador local)**:
   - Fijar variables de entorno permanentes (`[Environment]::SetEnvironmentVariable`) en perfil User para `JAVA_HOME`, `ANDROID_HOME`, `PATH`.
   - Arrancar emulador: `emulator -avd pixel_6_api34` (primer boot 2-3 min).
   - `npx expo run:android` desde `mobile/` → compila en local e instala en emulador.
   - Validar DnD + "Probar alarma" + "Parar" + `adb logcat` limpio.
4. **Si Hyper-V no funciona → Camino B (móvil físico + build local)**:
   - Configurar depuración USB en el móvil (Ajustes → Opciones de desarrollador).
   - Conectar vía USB + `adb devices` (confirmar que el móvil aparece).
   - `cd mobile/android && ./gradlew assembleRelease` → produce APK.
   - `adb install -r app/build/outputs/apk/release/app-release.apk` → instala en el móvil.
   - Probar DnD + "Probar alarma".
5. **Camino C (EAS #3) como fallback**: si ni emulador ni USB funcionan, esperar a que termine la build EAS.

### Paso 2 — Fase 7a (backend)

Ver checklist completo en `fases.md` §Fase 7a. Prioridades:
1. Las 5 trampas de migración primero (antes de borrar nada).
2. Fixes E2/E3/E4/E6 en el Poller/Estimador durante el refactor.
3. Contrato FCM D40 (push on-change).
4. Tests (~31 sobreviven intactos; reescribir poller/api/notifiers; añadir tests para E2/E3/E4).

### Paso 3 — Fase 7b (app Android v1)

Ver checklist en `fases.md` §Fase 7b. El `AlarmScheduler` (D40) es la pieza nueva central; Android SDK ya instalado (JDK 17 + SDK 34).

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
| Fase 7 — App móvil | 🔶 **En curso** — Spike: fix E1 aplicado commiteado, build EAS #3 en vuelo, Hyper-V pendiente de reinicio. SDK local instalado. Validación (emulador o dispositivo) pendiente. |

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
