# Avisador de alertas deportivas en tiempo real

Sistema de **alertas telefónicas** que avisa a un usuario **X minutos antes** de
que empiece un combate o partido concreto de deportes con **tarjeta escalonada**
(MMA, Boxeo, Tenis…).

## El problema

En deportes como MMA el horario real de un combate no es fijo: depende de cuánto
duren los combates anteriores de la tarjeta. Quien quiere ver un combate concreto
no sabe a qué hora empezará realmente, y acaba pendiente de la retransmisión
durante horas.

## La solución

El sistema **sigue la tarjeta en vivo** y estima el inicio del combate objetivo en
función del estado del combate anterior. Cuando el arranque es inminente, **llama
por teléfono** al usuario.

### Ejemplo

1. El usuario suscribe: *"Avísame 15 min antes del combate X vs Y de UFC 329"*.
2. El sistema monitoriza la card. Al terminar el combate anterior, recalcula el
   inicio estimado del combate objetivo.
3. Cuando `estimado − ahora ≤ 15 min`, dispara una **llamada** al usuario.

## Alcance

- **MVP**: MMA (UFC) vía la API pública de ESPN, multiusuario con panel de
  administración web, y alerta por llamada telefónica.
- **Más adelante**: Boxeo, Tenis, y otras ligas de MMA (Bellator/PFL).

## Stack

Python 3.12 · FastAPI · APScheduler · PostgreSQL · Redis · SQLAlchemy async ·
httpx · Jinja2 + HTMX · Twilio (llamadas).

## Documentación

- **Cómo montarlo y comandos** → [`AGENTS.md`](AGENTS.md)
- **Estado actual y próximo paso** → [`memoria/handoff.md`](memoria/handoff.md)
- **Diseño, decisiones, fases y fuentes de datos** → carpeta
  [`memoria/`](memoria/) (índice en `AGENTS.md`)

> La documentación viva del proyecto está modularizada en `memoria/`. Este README
> solo describe el **qué** y el **por qué**; el **cómo** y el detalle técnico viven
> en `memoria/` y `AGENTS.md`.
