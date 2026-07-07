# Contexto de la aplicación

> Visión del producto, caso de uso y alcance del avisador de alertas deportivas.

## Qué resuelve

Sistema de alertas telefónicas (llamada a SIM virtual) que avisa a un usuario
**X minutos antes** de que empiece un combate/partido concreto de deportes con
**tarjeta escalonada** (MMA, Boxeo, Tenis, etc.).

El problema: en deportes como MMA el horario real de un combate depende de la
duración de los combates anteriores de la tarjeta. El usuario quiere ser avisado
cuando **el combate que le interesa vaya a empezar pronto**, lo cual requiere
estimar el inicio en función del estado en vivo del combate anterior.

## Caso de uso típico

1. Usuario suscribe: "Avísame 15 min antes del combate Main Card de UFC XXX entre X vs Y".
2. Sistema sigue en vivo la tarjeta. Cuando el combate inmediatamente anterior
   termina (o está a punto de terminar), recalcula el inicio estimado del combate objetivo.
3. Cuando `estimado - ahora ≤ 15 min` → dispara llamada telefónica al usuario.

## Alcance confirmado (MVP)

- **Deportes prioritarios**: MMA (UFC) primero; Boxeo + Tenis más adelante (Fase 4).
- **Canal de alerta**: llamada telefónica (sin SMS/Telegram de respaldo por ahora).
  Proveedor SIM virtual: Twilio (Fase 5).
- **Usuarios**: multiusuario + frontend de administración web.
- **Tipo de alerta**: inicio inminente (X min antes, configurable por suscripción).

## Fuera del MVP

- Bellator/PFL, Boxeo y Tenis reales (Fase 4).
- Proveedor de llamadas real (Fase 5, Twilio).
- Scraping de fuentes secundarias.
