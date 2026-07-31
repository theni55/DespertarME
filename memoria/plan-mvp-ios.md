# Plan MVP iOS + cierre Android — dogfooding personal

> Plan para estabilizar el MVP Android en el dispositivo del compañero y arrancar el MVP iOS (owner), antes de plantear publicación. Complementa `plan-mvp-android-fable5.md` (ese cubre solo Android).

## 0. Contexto

- Objetivo actual: **NO publicar todavía**. Tener MVPs estables para pruebas personales — Android en el móvil del compañero, iOS en el móvil del owner (iPhone con iOS 26+).
- Restricciones conocidas:
  - Owner solo tiene acceso a un **Mac en la nube** (proveedor sin decidir), no un Mac físico.
  - Cuenta Apple Developer: se probará primero con **Apple ID gratuita** ("Personal Team"); si no alcanza, se paga el Programa ($99/año).
  - Apple confirma (developer.apple.com/support/compare-memberships, verificado 2026-07-21): cuenta gratuita permite testing on-device pero con certificados/perfiles que **caducan a los 7 días**, **sin ad-hoc distribution** y **sin TestFlight** (ambos exclusivos de pago). "Advanced app capabilities and services" aparece solo en la columna de pago — riesgo de que Push Notifications/AlarmKit avanzados lo requieran.
  - D40/D43 (decisiones ya cerradas) ya asumían: iOS requiere mínimo iOS 26 + AlarmKit, sin fallback a Critical Alert Entitlement, rewrite SwiftUI completo (no se reutiliza nada de TS del spike Expo).

## 1. Pista Android (compañero) — cerrar lo pendiente

- [ ] **Validación con evento real**: UFC Fight Night Ankalaev vs Guskov, 25 julio 2026, 13:00 UTC. Confirma que el poller detecta transiciones reales de ESPN (no solo simuladas) y dispara la reprogramación de alarma vía FCM (modelo D45). Crítico para ambas plataformas ya que comparten backend.
- [ ] **Doze validation**: `adb shell dumpsys deviceidle force-idle` + verificar que `setAlarmClock` despierta puntualmente. Pendiente desde Fase E, nunca ejecutada formalmente.
- [ ] **Sideload en el móvil del compañero**: compartir el `.apk` debug (ya apunta a Railway desde Sesión 20) + activar "orígenes desconocidos", o `adb install` con acceso físico al cable un momento. Sin Play Store, sin firma de release.
- [ ] **Prueba multi-dispositivo real**: confirmar que 2 móviles con suscripciones distintas simultáneas reciben sus alarmas de forma independiente (el modelo `Device` ya lo soporta por diseño, pero nunca se ha probado con 2 dispositivos físicos a la vez).

## 2. Fix de backend previo a iOS (bloqueante, pequeño)

- [ ] `src/app/notifiers/fcm.py`: el `FcmNotifier.send()` construye el mensaje con `android=AndroidConfig(priority="high")` pero **sin `ApnsConfig`**. Para que un push data-only despierte la app iOS en background (necesario para que `handleUpdate()` reprograme la alarma con la app cerrada), FCM necesita explícitamente:
  ```python
  apns_config=messaging.APNSConfig(
      headers={"apns-priority": "5", "apns-push-type": "background"},
      payload=messaging.APNSPayload(aps=messaging.Aps(content_available=True)),
  )
  ```
  Cambio aislado, no afecta el comportamiento actual de Android (FCM ignora `ApnsConfig` para tokens Android).
- [ ] Tests de regresión en `tests/test_notifiers.py` para el nuevo `ApnsConfig`.

## 3. Fase 0 — Spike de riesgo iOS (antes de construir el MVP completo)

**Objetivo:** confirmar con evidencia real si la cuenta Apple gratuita alcanza para AlarmKit + Push, antes de invertir tiempo en las 5 pantallas completas.

**Infraestructura elegida:**
- **Compilación**: GitHub Actions con runner `macos-14` sobre el repo `theni55/DespertarME` (gratis dentro de límites, no requiere login de Apple ID para compilar sin firma — `CODE_SIGNING_ALLOWED=NO`).
- **Instalación/firma en el iPhone**: **AltStore/AltServer** (AltServer soporta host **Windows** — se instala en este mismo PC). Empareja el iPhone una vez vía USB/red local a este PC, firma el `.ipa` sin firmar producido por CI usando la Apple ID gratuita del owner (replica el protocolo de aprovisionamiento personal-team de Xcode sin pasar por una sesión interactiva), y refresca el certificado cada ~6-7 días desde el mismo PC — sin necesitar Mac físico en ningún momento del ciclo.
- **Riesgo abierto explícito**: si AltStore consigue empaquetar correctamente las capabilities de AlarmKit y Push Notifications en el perfil gratuito, o si Apple las restringe a cuentas de pago. Esto es exactamente lo que valida el spike.

**Pasos:**
1. [ ] Crear proyecto Xcode mínimo `DespertarMeSpike` (un solo botón) en una carpeta iOS del monorepo.
2. [ ] Workflow de GitHub Actions (`macos-14`) que compile el target sin firma y publique el `.app`/`.ipa` como artifact.
3. [ ] Instalar AltServer en este PC, emparejar el iPhone del owner, sideload del `.ipa` inicial (app vacía) para validar el pipeline de extremo a extremo.
4. [ ] Añadir, un cambio aislado cada vez:
   - `NSAlarmKitUsageDescription` + llamada trivial `AlarmManager.shared.schedule(...)` → ¿corre sin error de entitlement?
   - Capability Push Notifications + Firebase Messaging SDK (añadiendo la app iOS al proyecto Firebase ya existente `despertarme-73d00`) → ¿recibe un push data-only de prueba con la app en background?
5. [ ] **Criterio de salida**: documentar en `memoria/decisiones.md` (nueva decisión numerada) si la cuenta gratuita alcanza o si hace falta el Programa de pago, con la evidencia concreta de qué falló (mensaje de error de Xcode/AltServer, comportamiento del push, etc.).

## 4. Fase 2 — MVP iOS completo (condicionado al resultado de la Fase 0)

Rewrite SwiftUI completo (D43: no se reutiliza nada del spike Expo/TS), replicando el alcance ya construido en Android:

- [ ] `HomeScreen`, `EventListScreen`, `EventDetailScreen` (suscripción con selector de lead minutes), `SubscriptionsScreen` (cancelar + historial), `SettingsScreen` (device_id, permisos).
- [ ] Capa de red: `URLSession` + `Codable`, mismo contrato de API ya documentado en `/docs` (Railway).
- [ ] Persistencia `device_id` UUID v4 en Keychain (equivalente a DataStore Preferences de Android).
- [ ] AlarmKit: `AlarmManager.schedule(id:configuration:)` equivalente a `AlarmScheduler`/`setAlarmClock` de Android, mismo modelo D45 (cushion +1 min, ring-once, reprogramación solo vía push `update`).
- [ ] Firebase Messaging SDK: manejo de `update`/`started`/`cancelled`/`fire`, mismo contrato de payload que consume `DespertarMeFirebaseService.kt` en Android.
- [ ] Registro de `Device` con `platform="ios"` contra el backend ya existente (sin cambios de schema, el campo ya existe).

## 5. Fuera de alcance de este plan (explícitamente diferido)

- Play Store / App Store: cuenta de desarrollador, listing, builds firmados de release, ProGuard, keystore de release Android.
- Hardening de seguridad de `X-Device-Id` (sin auth real hoy) — aceptable mientras sean solo 2 dispositivos de confianza en pruebas personales.
- Fix del bug de auditoría en `alert_log` (falta `message_type` en el UNIQUE) — no bloquea funcionalidad, solo pierde filas de auditoría en colisiones.
- Validación estricta de UUID v4 en `DeviceCreate`.
- Sonido custom `alarm.ogg`, observabilidad del backend (Sentry/alertas), verificación de persistencia de Redis en Railway.

## 6. Preguntas abiertas / decisiones pendientes del owner

- Confirmar si se acepta el spike vía GitHub Actions + AltStore, o si se prefiere explorar otro proveedor de Mac en la nube con acceso GUI interactivo (ej. MacinCloud) para el spike inicial.
- Tras el resultado de la Fase 0: decidir formalmente pagar el Programa Apple Developer o seguir con las limitaciones de la cuenta gratuita (registrar como nueva decisión en `decisiones.md`).
