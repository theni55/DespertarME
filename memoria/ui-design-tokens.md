# Tokens de diseño (referencia Winamax → DespertarME)

> Tokens extraídos de las capturas Winamax (`memoria/assets/imagen_referencia_1..3.jpeg`) y su adaptación al dominio DespertarME (sin apuestas). Fuente de verdad para el rediseño visual de la app Kotlin (Sesión 23, piloto Home).

## Metodología

Ingeniería inversa visual de las 3 capturas (home con cards de partidos, home scrolleada
con "Jugadores destacados", pantalla Buscar). Los valores hex son estimaciones por
inspección; lo que importa es la **relación** entre tokens (jerarquía, contraste,
radios), no la igualdad exacta con Winamax.

## Paleta observada en Winamax

| Token Winamax (observado) | Valor aprox. | Uso en Winamax |
|---------------------------|--------------|----------------|
| Fondo app | `#000000`–`#0D0D12` | Fondo global, bottom nav |
| Superficie card | fotos full-bleed + scrim | Cards de partido |
| Superficie fila/lista | `#1C1C22` | Filas de Buscar, chips deportes |
| Rojo marca | `#E4002B` | Logo, CTA "Conectarse", cifras de cuota |
| Texto primario | `#FFFFFF` | Títulos, nombres de equipos |
| Texto secundario | `#9E9EA7` | Metadatos, porcentajes |
| Strip de card | degradado azul/verde | Header de card con competición |
| Borde de card | degradado sutil (verde→naranja) | Contorno de la card destacada |
| CTA de cuota | blanco `#FFFFFF`, texto rojo oscuro | Botones de apuesta (pills) |

## Rasgos estructurales observados

- **Card de partido**: header strip (~40dp) con icono de competición + nombre; cuerpo
  = foto protagonista full-bleed; abajo, fila de 3 elementos (equipo | hora | equipo)
  superpuesta sobre la foto; cierre con fila de CTAs pill.
- **Radios**: cards ~16–20dp; pills/CTAs ~10–12dp; chips circulares.
- **Tipografía**: sans-serif bold/black para títulos y cifras; secundarios en regular.
  Títulos de sección en sentence case ("Competiciones destacadas"), ~22sp bold.
- **Bottom nav**: negra pura, solo iconos (sin labels), 6 destinos.
- **Hora centrada** en la card entre los dos contendientes ("Do. 21:00" / "Mañana 23:00").

## Adaptación DespertarME (tokens aplicados en `ui/theme/Color.kt`)

Sin apuestas: los CTAs de cuota se sustituyen por **un único CTA "Avísame"**.
La paleta conserva el rojo UFC ya existente (`#E50914`, D35/D43) como color de marca
en lugar del `#E4002B` de Winamax — son casi idénticos y el nuestro ya está en producción.

| Token DespertarME | Valor | Equivalencia Winamax |
|-------------------|-------|----------------------|
| `BackgroundDark` | `#0A0A0A` | Fondo app (ya existía) |
| `SurfaceDark` | `#1A1A1A` | Superficie fila/lista (ya existía) |
| `SurfaceVariantDark` | `#2A2A2A` | Chips/inputs (ya existía) |
| `UfcRed` | `#E50914` | Rojo marca (ya existía) |
| `UfcRedDeep` | `#7F050C` | Fin del degradado del strip de card (nuevo) |
| `PosterSurface` | `#15151B` | Fondo del área de póster de la card (nuevo) |
| `TextPrimary` / `TextSecondary` | `#FFFFFF` / `#B8B8B8` | Texto (ya existían) |
| `RedCorner` / `BlueCorner` | `#E50914` / `#3B82F6` | Esquinas roja/azul del combate (dominio MMA, ya existían) |
| `AccentGreen` | `#4ADE80` | Estados OK (ya se usaba inline; promovido a token) |

### Estructura de la card de evento (Home)

1. **Strip superior**: degradado horizontal `UfcRed → UfcRedDeep`, badge "UFC" + "MMA · N combates".
2. **Área de póster**: `PosterSurface` con glows radiales `RedCorner`/`BlueCorner` (esquinas
   del octágono) + headshots reales del main event (izq/dcha) + **fecha y hora centradas**
   (patrón Winamax "equipo | hora | equipo").
3. **Pie**: nombre del evento (bold) + main event (secundario) + CTA pill "Avísame" rojo full-width.

### Radios y espaciado

- Card: `18.dp`; CTA pill: `50%` (stadium); strip: sin radio propio (lo recorta la card).
- Espaciado en escala de 4dp: 4/8/12/16/20/24.
- Bottom nav: `BackgroundDark` (negro, como Winamax), 3 destinos **con** labels
  (desviación consciente de Winamax: con solo 3 tabs el label ayuda y cuesta 0).

## Pendiente para sesiones futuras

- Replicar estos tokens en `EventDetailScreen`/`BoutCard` (fuera del piloto).
- Evaluar tipografía Inter embebida (diferida en Sesión 17, sigue diferida).
