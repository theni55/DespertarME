# Validación de sesión Fable 5 — Piloto Home estilo Winamax

> Documento de validación previo a lanzar la sesión de Fable 5 vía `/goal`. Resultado de una sesión de grilling (skill `grill-with-docs`, modo lightweight) sobre `memoria/plan-ui-redesign-winamax.md`. Resuelve las ambigüedades que el plan original dejaba abiertas explícitamente, limitando el alcance a un piloto de una sola pantalla.

## Alcance de la sesión

**Piloto: solo `HomeScreen.kt` + los cambios mínimos de navegación que dependen de él.** No se toca `EventDetailScreen.kt` ni el rediseño del `BoutCard` en esta sesión — eso se replica en una sesión posterior si el piloto valida el approach.

## Estado actual (verificado en código, no en el plan)

`HomeScreen.kt` hoy:
- Hero **estático único** (`R.drawable.hero`, poster hardcodeado de UFC 329 McGregor vs Holloway 2), decisión cerrada en Sesión 15 ("se quedará así la imagen") — **esta sesión la reabre**, documentar como nueva decisión si se formaliza.
- Un solo botón "Avísame" → `onNextEvent()` (navegación a un evento único, no hay lista).
- Botón "Probar/Parar sonido" (test manual de `AlarmService`, Fase E).
- Bottom nav actual: **4 destinos** (Home / Eventos / Mis Alertas / Ajustes).
- `EventListScreen.kt` ya existe y usa fallback visual (gradiente rojo + icono guante) porque **ESPN no sirve `image_url` por evento (decisión D42)** — limitación de datos real, no solo de UI.
- Scope de datos real hoy: **solo MMA/UFC** (Boxeo/Tenis/Bellator fuera del MVP, D11/D12). "Posters por deporte/liga" del plan Winamax se reduce en la práctica a un único poster genérico UFC.

## Decisiones resueltas en esta sesión de grilling

| # | Pregunta | Decisión |
|---|----------|----------|
| 1 | Alcance de la sesión Fable | Piloto de una sola pantalla (Home), no el rediseño completo |
| 2 | Quién extrae tokens de diseño (paleta/spacing/tipografía) | Fable, como primer paso de su propia sesión (usando `design-reverse-engineering` u otra vía) |
| 3-4 | Criterio de "destacado" en Home | Lista real de N próximos eventos vía API (ej. `GET /api/events` ordenado por fecha, top 3-5), no el evento único actual |
| 5-6 | Imagen de fondo por card (dado que ESPN no sirve `image_url`, D42) | Generar/asignar posters genéricos por liga (en la práctica: 1 poster genérico UFC) — **Fable lo gestiona en su propia sesión**, no como paso previo mío |
| 8 | Navegación del CTA por card | Cada card navega a `event/{id}` propio; se elimina el botón global único `onNextEvent` |
| 9 | Botón "Probar/Parar sonido" | Se mueve a `SettingsScreen` (Ajustes), sale de Home |
| 10 | ¿El piloto toca la bottom nav? | Sí — se aplica ya la nav reducida a 3 destinos (Buscar/Home/Alertas) como parte de este piloto |
| 11 | Acceso a Ajustes tras quitarlo de la nav | Icono ⚙️ en el header de "Mis alertas" |
| 12 | Destino "Buscar" | **Sin respuesta del owner (timeout).** Default aplicado: "Buscar" = `EventListScreen` renombrado/reposicionado en la nav tal cual, **sin fusión visual profunda todavía**. La fusión real (Home absorbe destacados / Buscar como buscador+listado completo) queda fuera de este piloto — **revisar con Javier antes de lanzar si esto no es lo que quería.** |

## ⚠️ Punto a confirmar antes de lanzar (no bloqueante, pero pendiente)

La decisión #12 se tomó por default ante ausencia de respuesta, no por confirmación explícita. Es la única de las 12 sin luz verde directa. Recomendación: pasar por esto con Javier en 30 segundos antes de darle `/goal` a Fable, o aceptar el default (es el camino de menor riesgo — no toca `EventListScreen` por dentro, solo lo reengancha en la nav).

## Principio del owner: esto es un MVP, no dogma

Ninguna decisión de este documento (ni D1–D45 de `decisiones.md`) es sagrada. Es un MVP — la intención explícita del owner es **mejorar**, aunque eso contradiga premisas con las que se arrancó. Si durante el rediseño Fable encuentra un flaw, una mejor alternativa técnica o de UX a algo ya decidido aquí o en sesiones previas:

- **No lo ignores ni lo fuerces a encajar** en la decisión vieja solo por respetar la convención de "no reabrir sin justificar".
- **Sí documenta la desviación**: qué se cambió, por qué, y como nueva decisión numerada en `memoria/decisiones.md` (D46+). La regla sigue siendo "no reescribas la historia" — las decisiones viejas no se editan, se supersede con una nueva y trazable.
- Prioriza terminar con algo mejor sobre terminar exactamente lo que este documento predijo. Si el plan de aquí resulta subóptimo a medio camino, cambia de rumbo y dilo en `handoff.md`.

## Fuera de alcance de este piloto (documentado para no reabrir sin querer)

- Rediseño de `BoutCard` / `EventDetailScreen.kt` (queda para sesión siguiente).
- Fusión visual profunda Buscar/EventList (ver punto pendiente arriba).
- Multi-deporte en posters (hoy solo aplica a UFC).
- Cualquier decisión D1–D45 ya cerrada en `memoria/decisiones.md` — no reabrir sin justificar una nueva decisión numerada (D46 en adelante).

## Candidata a ADR / decisión formal (D46)

**Reabrir la decisión de Sesión 15** ("hero se queda así") a favor de lista de cards con posters genéricos por liga. Es difícil de revertir (cambia estructura de datos de Home, no solo estilo), sorprendente sin contexto (contradice una decisión cerrada previa) y resultado de un trade-off real (foto real por evento no es posible por limitación de ESPN D42, se opta por aproximación genérica). **Recomendado documentar como D46 en `memoria/decisiones.md` antes o durante la sesión de Fable.**

## Instrucciones operativas para Fable 5 (a añadir al prompt de `/goal`)

1. Rama `dev`, no mergear a `main` sin confirmación (per convención del repo).
2. Esto es un MVP: si encuentras un flaw o una mejor alternativa a cualquier decisión previa (D1–D45 o las de este documento), no la fuerces por respetar la convención — cámbiala y documenta el porqué como nueva decisión numerada (D46+) en `decisiones.md`. No edites decisiones viejas, supersédelas con trazabilidad.
3. Primer paso: extraer tokens de diseño de las capturas Winamax (`design-reverse-engineering` u otra vía) antes de tocar Compose.
4. Segundo paso: generar/gestionar el poster genérico UFC como asset.
5. Tercer paso: implementar `HomeScreen.kt` con lista de cards (datos reales vía API, no mock), CTA por card a `event/{id}`, sin botón global.
6. Mover "Probar/Parar sonido" a `SettingsScreen`.
7. Reducir bottom nav a 3 destinos (Buscar/Home/Alertas); Ajustes accesible vía icono ⚙️ en header de "Mis alertas"; "Buscar" = `EventListScreen` reposicionado sin fusión profunda (salvo que Javier corrija el punto pendiente antes de lanzar).
8. Actualizar `handoff.md`, `fases.md`, `bitacora.md` al final de la sesión (convención estricta, hook lo verifica).
9. Criterio de aceptación: smoke visual en emulador — Home muestra N cards con datos reales de próximos eventos UFC, poster genérico de fondo, CTA por card navega a `EventDetailScreen` correcto, nav de 3 destinos funcional, Ajustes accesible desde Mis Alertas, sin crashes en logcat.
