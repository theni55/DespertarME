# Contexto de la aplicación

> Visión del producto, caso de uso y alcance del avisador de alertas deportivas.

## Qué resuelve

Sistema de alertas telefónicas (alarma local en el móvil, tipo despertador) que
avisa a un usuario **X minutos antes** de que empiece un combate/partido concreto
de deportes con **tarjeta escalonada** o **cuartos** (MMA, Tenis, NBA, NFL,
Fútbol).

El problema: en deportes como MMA el horario real de un combate no es fijo —
depende de la duración de los combates anteriores de la tarjeta. El usuario
quiere ser avisado **cuando su combate vaya a empezar pronto**, lo cual requiere
estimar el inicio en función del estado en vivo del combate anterior.

## Caso de uso típico

1. Usuario abre la app (sin cuenta) y se suscribe: "Avísame 15 min antes del
   combate Main Card de UFC XXX entre X vs Y" (o "cuando empiece" un cuarto NBA).
2. El backend sigue la tarjeta en vivo. Cuando el combate inmediatamente anterior
   termina (o está a punto de terminar), recalcula el inicio estimado del combate
   objetivo y envía un push FCM `update`.
3. La app programa una alarma local exacta (`AlarmManager.setAlarmClock`) que
   suena `estimated_start − lead`, incluso con el móvil en silencio/DnD.

## Alcance actual (MVP)

- **Deportes**: MMA (UFC), Tenis (ATP/WTA), NBA, NFL y Fútbol — vía ESPN Core API.
- **Canal de alerta**: alarma local exacta en Android (Kotlin/Compose), con FCM
  como "reprogramador" de la estimación (D40/D45).
- **Actores**: `Device` (FCM token) sin cuentas de usuario; header `X-Device-Id`.
- **Backend**: FastAPI + Postgres + Redis en Railway, poller multi-sport.

## Fuera del MVP

- iOS (Fase 7d, vía AlarmKit de iOS 26).
- Distribución en Play Store (release keystore, ProGuard, cuenta $25).
- Admin web de devices, Boxeo, Bellator/PFL.
