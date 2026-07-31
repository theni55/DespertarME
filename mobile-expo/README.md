# DespertarME · Spike bypass-silent (Fase 7-Spike, D39)

> Spike mínimo para validar **solo** una cosa: `TYPE_ALARM` suena con el móvil
> Android físico en modo No Molestar (DnD). Sin FCM, sin full-screen intent,
> sin secure-store, sin MVP carátula. 1 pantalla + 2 botones + 2 ficheros Kotlin.

## Estructura

```
mobile/
├─ App.tsx                                   # UI: botones Probar/Parar → AlarmModule
├─ app.json                                   # package com.despertarme.spike + permisos
├─ eas.json                                   # perfil development (APK internal)
└─ android/app/src/main/
   ├─ AndroidManifest.xml                     # <service> AlarmService type=mediaPlayback
   └─ java/com/despertarme/spike/
      ├─ MainActivity.kt                      # autogen Expo prebuild
      ├─ MainApplication.kt                   # registra AlarmPackage
      └─ alarm/
         ├─ AlarmModule.kt                    # canal IMPORTANCE_HIGH + setBypassDnd
         ├─ AlarmService.kt                   # foreground service + TYPE_ALARM loop
         └─ AlarmPackage.kt                   # registro del módulo en el bridge RN
```

## Cómo lanzar la build (EAS, ~30-45 min cloud)

```powershell
cd mobile
npx eas login                          # cuenta Expo del owner (expo.dev, gratis)
npx eas build --platform android --profile development
```

Cuando termine: EAS devuelve una URL tipo
`https://expo.dev/artifacts/eas/<hash>.apk`. Abrirla desde el móvil.

## Cómo instalar en el móvil

1. Abrir la URL en el navegador del móvil → descarga `despertarme-spike.apk`.
2. Al instalar: Android pedirá "Origen desconocido" para el navegador → aceptar.
3. Abrir **DespertarME Spike**.

## Permisos que hay que dar a mano (solo una vez)

Para que el canal `IMPORTANCE_HIGH` con `setBypassDnd(true)` atraviese el DnD:

1. **Notificaciones**: Settings → Apps → DespertarME → Notificaciones → ON.
2. **Override Do Not Disturb**: en la misma pantalla, toggle
   "Anular el modo No Molestar" / "Override Do Not Disturb" → ON.
   (La app abre esta pantalla automáticamente la 1ª vez que tocas "Probar
   alarma" si aún no lo tienes concedido.)
3. **Volumen de alarma**: Settings → Sonido → Volumen → Alarma → máximo.

## Cómo probar

1. Pon el móvil en **modo No Molestar** (icono luna, o ajustes rápidos).
2. Abre DespertarME Spike.
3. Toca **"Probar alarma"** → debería sonar `TYPE_ALARM` aunque el móvil
   esté en silencio/DnD.
4. Toca **"Parar"** → debería callar.

## Si no suena

Diagnóstico en <2h:

```powershell
# Sin Android Studio: descargar platform-tools standalone (~5MB)
# https://developer.android.com/tools/releases/platform-tools
# Activar Opciones de desarrollador + USB debugging en móvil, conectar por USB
.\adb logcat | findstr /I "despertarme AlarmService AlarmModule"
```

Mirar:
- `NotificationChannel` creado con `bypassDnd=true`? Si no, permiso
  ACCESS_NOTIFICATION_POLICY denegado.
- `startForeground` lanza SecurityException? Tipo de FGS mal declarado.
- `Ringtone` null? `TYPE_ALARM` no disponible en el dispositivo → fallback a
  TYPE_RINGTONE (sin bypass DnD en algunos OEM).

Casos OEM problemáticos (Xiaomi/MIUI, Samsung, Huawei): restricciones extra de
autostart/batería. Settings → Apps → DespertarME → Batería → Sin
restricciones.

## Lo que NO incluye este spike

- FCM (Firebase)                  → Fase 7a
- UI AlarmScreen full-screen      → Fase 7b
- Navegación Expo Router          → Fase 7b
- `expo-secure-store` (device_id) → Fase 7a
- Sonido custom embebido (.ogg)   → Fase 7b (aquí usamos TYPE_ALARM del sistema)

## Limpiar

El código Kotlin a ciegas (sin Android Studio para debugear) es lo frágil.
Cuanto menos código, menos probabilidades de que la APK crashee a la primera.
Si la primera build crashea, aislar en `logcat` y arreglar; otra build cuesta
~30-45 min.