# Plan: rediseño UI Android inspirado en Winamax

> Plan de trabajo para rediseñar la UI de `mobile-kotlin/` (Home, EventDetail, bottom nav) tomando como referencia visual la app Winamax. Fase de documentación — sin cambios de código todavía.

## Contexto

El owner quiere mejorar sustancialmente el aspecto visual de la app Android
(actual: Home con hero image + lista de `BoutCard`, ver Sesiones 15-18 en
`handoff.md`). Referencia: capturas de Winamax (adjuntas en el chat, guardadas
en `/root/.hermes/image_cache/img_a8bb5ebd6e15.jpg` y
`img_fc41b17df807.jpg`).

## Análisis visual de las referencias

### Home / listado de eventos destacados

- Fondo dark casi negro (`#0A0A0A`-ish, ya usado en la app).
- Cards grandes, edge-to-edge, con **foto real del deportista/evento de fondo**
  (no recortada, composición dejando ver ambos contendientes cuando aplica).
- Header de card: competición + fecha en gris pequeño arriba, icono de video
  destacado (esquina superior derecha) cuando hay contenido en directo.
- Banderas/iconos circulares de los contendientes superpuestos sobre la foto.
- Hora del evento centrada sobre la imagen, tipografía grande blanca.
- Nombres de contendientes debajo de la foto, alineados a la posición de
  cada bandera.
- Dos "chips" pastilla blanca por debajo con la cuota/dato destacado — el
  favorito lleva borde rojo. Barra de probabilidad fina debajo (5%/95%).
- Bottom nav: iconos flat, ícono activo con fondo circular blanco resaltado
  y centrado.

### Detalle de evento (listado de partidos/combates)

- Header: back arrow + breadcrumb de competición, título grande centrado
  ("Partidos"), icono de stats a la derecha.
- Fila de filtros tipo chip horizontal scrolleable (Partido/Sets/Juegos...).
- Lista vertical de cards por partido/combate:
  - Badge de ronda/fase arriba a la izquierda.
  - Banderas/iconos de contendientes a los lados.
  - Centro: marcador en vivo (con parciales) o "hora"/"Mañana HH:MM" si no
    ha empezado. Punto ámbar para indicar en directo.
  - Cuotas en pastillas blancas debajo, ganador probable con borde rojo.
  - Barra de probabilidad fina bajo cada pastilla cuando aplica.

## Traducción al dominio DespertarME

Winamax vende apuestas; nosotros vendemos "que no te pierdas el combate
siguiente". Hay que adaptar, no calcar 1:1:

| Winamax | DespertarME |
|---|---|
| Cuota + % probabilidad | No aplica (no hay apuestas). Sustituir por: estado del combate (pre/in/post) + tiempo estimado de inicio, o botón "Avísame" |
| Marcador en vivo con parciales | Estado ESPN del combate previo (round actual, si aplica) |
| Chips de filtro (Partido/Sets/Juegos) | Filtro por segmento de cartelera (Main Card / Prelims / Early Prelims) |
| Card de evento destacado en Home | Card de evento UFC/deporte destacado con cartel/póster + hora estimada del primer combate |
| Card de partido en detalle | `BoutCard` ya existente — mismo dato (peleadores + headshots) pero maquetado como card Winamax con badge de segmento, hora/estado, y CTA "Avísame N min antes" en vez de cuotas |

## Bottom nav — spec exacta pedida por el owner

Solo **3 destinos** (no 4 como ahora ni 6 como Winamax):

1. **Buscar** — izquierda. Lista de deportes/eventos, con buscador para
   encontrar uno concreto.
2. **Home** — centro, **visualmente destacado** (icono más grande y/o
   badge circular, replicando el resaltado del home activo en Winamax).
   Es el destino por defecto al abrir la app.
3. **Mis alertas** — derecha. Sustituye a la pantalla `SubscriptionsScreen`
   actual (activas + historial), ya existe el ViewModel — solo cambia su
   posición/icono en la nav bar.

Se elimina `EventListScreen` como destino de nav independiente: pasa a vivir
dentro de "Buscar" (o Home la absorbe como sección "eventos destacados" y
Buscar es solo el buscador+listado completo — a decidir en el diseño
detallado). `SettingsScreen` deja de tener icono propio en la bottom bar —
se reubica como acción secundaria (ej. icono de ajustes en el header de
"Mis alertas" o del propio perfil/device).

## Pantallas afectadas (mobile-kotlin/)

- `ui/screens/HomeScreen.kt` — pasar de hero único a lista de cards de
  eventos destacados estilo Winamax (foto + hora + CTA).
- `ui/screens/EventListScreen.kt` — se fusiona con la nueva pantalla
  "Buscar" (filtro por deporte + búsqueda).
- `ui/screens/EventDetailScreen.kt` — rediseño de `BoutCard` con el layout
  de card de partido Winamax (badge segmento, banderas/headshots,
  hora/estado, CTA avisar).
- `ui/screens/SubscriptionsScreen.kt` — pasa a ser destino nav "Mis
  alertas" (ya existe, revisar visual).
- `MainActivity.kt` / `AppGraph` — bottom nav reducida a 3 destinos,
  ordenado Buscar-Home-Alertas, Home con estilo resaltado.
- `ui/theme/` — puede necesitar tokens nuevos (gradientes de card, colores
  de badge por segmento, estilos de chip/pastilla).

## Siguiente paso (antes de tocar código)

Investigar skills/herramientas de Hermes que puedan potenciar este rediseño
antes de escribir Compose a mano:

- `design-reverse-engineering` — para extraer tokens de diseño (paleta,
  spacing, tipografía) directamente de las capturas de Winamax de forma
  sistemática.
- `popular-web-designs` / `claude-design` — aunque son HTML/web, pueden
  servir de referencia de composición aunque el target sea Compose nativo.
- `excalidraw` — bocetar el layout de cada pantalla antes de codear.
- Buscar si existe algo específico de Jetpack Compose / Material3 theming
  en el catálogo de skills o si hay que crear una skill nueva
  "android-compose-ui-design" tras esta investigación.
- Revisar si merece la pena generar assets (fondos degradados, iconos
  custom) vía `image_generate` en vez de vectores Compose puros.

**No se ha escrito código todavía.** Este documento es solo el plan y el
análisis de referencia. El siguiente mensaje del owner debe autorizar la
fase de investigación de herramientas antes de empezar a implementar.

## Referencias visuales

- Home Winamax: `/root/.hermes/image_cache/img_a8bb5ebd6e15.jpg`
- Detalle evento Winamax: `/root/.hermes/image_cache/img_fc41b17df807.jpg`
