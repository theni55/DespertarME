# Plan: fixes UI multi-sport + cierre rama tenis-nba

> Plan por fases con checkboxes para la sesión de goal: fix E5, acordeones tenis, Home mixto, card NBA unificada, baseUrl Railway, merge a dev y deploy. Rama `feature/tenis-nba`.

---

## Contexto

La rama `feature/tenis-nba` (HEAD `8d29d1e`) tiene backend + Android funcionales
para MMA + Tenis + NBA, verificados en emulador contra backend local. Antes del
merge a `dev` y deploy a Railway, el owner ha pedido 3 mejoras de UI y queda
pendiente el fix E5 del handoff.

**Regla general:** cada fase termina con `assembleDebug` verde. Las fases de
backend no aplican (todo es Android salvo la Fase 5). Tests backend deben seguir
106/106 al final. Convenciones del proyecto en `memoria/convenciones.md`
(código en inglés, docs en español, type hints, ruff/black/pytest antes de commit).

---

## Fase 1 — Fix E5: `catch (Throwable)` → `catch (Exception)`

- [x] `CompetitionsViewModel.kt`: cambiar `catch (Throwable)` por `catch (Exception)`
      en `load()`. Motivo: `Throwable` atrapa `CancellationException` y las
      corutinas canceladas escriben error al state en vez de morir limpiamente.
- [x] `EventDetailViewModel.kt`: ídem.
- [x] Revisar si hay más `catch (Throwable)` en otros ViewModels (`HomeViewModel`,
      `EventListViewModel`, `SubscriptionsViewModel`) y aplicar el mismo fix.
- [x] Build verde. Commit: `fix(mobile): catch Exception en vez de Throwable en ViewModels`

## Fase 2 — Tenis: acordeones ATP/WTA en CompetitionsScreen

**Problema:** al entrar en Tenis desde Buscar, todos los torneos ATP + WTA salen
en lista plana — demasiados elementos.

- [x] `CompetitionsScreen.kt`: sustituir las dos secciones planas por 2 headers
      colapsables ("ATP" y "WTA") estilo acordeón: header clicable con chevron
      que rota al expandir (animación con `animateFloatAsState` o
      `AnimatedVisibility` para el contenido).
- [x] **Ambos colapsados por defecto** al entrar (decisión del owner).
- [x] Estado de expansión: `remember { mutableStateOf(false) }` por sección (no
      hace falta ViewModel; se pierde al navegar y es aceptable).
- [x] Al expandir se muestran los torneos de ese circuito; tap en torneo →
      EventDetail (flujo actual sin cambios).
- [x] Mantener keys compuestas de LazyColumn (`"atp-${id}"` / `"wta-${id}"`) —
      pitfall E1 Sesión 24.
- [ ] Smoke en emulador: Buscar → Tenis → 2 acordeones cerrados → expandir ATP →
      torneos → tap → partidos.
- [x] Commit: `feat(mobile): acordeones ATP/WTA en pantalla de competiciones de tenis`

## Fase 3 — Home: 1 destacado por deporte + resto cronológico

**Problema:** Home muestra top 4 por fecha → el tenis (eventos más próximos)
monopoliza todas las cards.

- [x] `HomeViewModel.kt`: cambiar el merge de los 4 fetches paralelos
      (mma, atp, wta, nba):
      1. Elegir el evento más próximo de **cada deporte** (MMA, Tenis
         [atp+wta combinados], NBA) → hasta 3 destacados.
      2. Añadir 2-3 eventos más por cronología pura, cualquier deporte,
         **deduplicando** los ya elegidos.
      3. Si un deporte no tiene eventos próximos, su hueco lo llena la cronología.
- [x] Orden final de la lista: los destacados también ordenados por fecha (no
      bloques artificiales por deporte).
- [x] Mantener keys compuestas `"${sport}-${league}-${id}"`.
- [ ] Smoke en emulador: Home muestra al menos 1 card de cada deporte con eventos.
- [x] Commit: `feat(mobile): home garantiza un evento destacado por deporte`

## Fase 4 — NBA: card única por partido con avisos por cuarto

**Problema:** el backend sirve 4 bouts sintéticos Q1-Q4 por partido NBA y
EventDetail los renderiza como 4 cards → parecen 4 partidos distintos. En el
resto de deportes hay 1 card por enfrentamiento.

- [x] `EventDetailScreen.kt`: para sport=nba, agrupar los 4 bouts del mismo
      partido en **una sola card**:
      - Cabecera: logos + nombres de los equipos (una sola vez).
      - Dentro: 4 filas de aviso — "Inicio del partido" / "2º cuarto" /
        "3º cuarto" / "4º cuarto".
      - Fila Q1: selector de lead 5/10/15/30 (comportamiento actual).
      - Filas Q2-Q4: chip único "Cuando empieza" (lead=0, comportamiento actual).
      - Cada fila suscribe/cancela contra su `bout_id` propio (`{eventId}_qN`).
      - Sugerencia anti-densidad: mostrar siempre la fila "Inicio del partido" y
        agrupar Q2-Q4 bajo un desplegable "Avisos por cuarto ▾" dentro de la
        card. Criterio final: que NO parezcan 4 partidos.
- [x] **Solo UI**: cero cambios de API/backend. La agrupación es por `eventId`
      (o prefijo del bout id) en la capa de presentación.
- [x] Revisar que el estado "Avisando ✓" por cuarto se refleje bien en cada fila.
- [ ] Smoke en emulador: EventDetail NBA muestra 1 card por partido; suscribirse
      a Q1 y a un cuarto; verificar en Mis Alertas que salen las dos con labels
      correctos ("Inicio" / "Cuarto #N").
- [x] Commit: `feat(mobile): card NBA unificada con avisos por cuarto agrupados`

## Fase 5 — baseUrl Railway + merge a dev + deploy

- [x] `AppContainer.kt`: restaurar `baseUrl` a
      `https://despertarme-production.up.railway.app/` (ahora apunta a
      `http://10.0.2.2:8000/` para desarrollo local).
- [x] Commit: `chore(mobile): restaurar baseUrl Railway para deploy`
- [x] Backend: `pytest` (106/106), `ruff check`, `black --check`, `mypy src/app`
      limpios antes del merge.
- [ ] Merge `feature/tenis-nba` → `dev` (⚠️ coordinar con el owner si theni55
      está trabajando sobre `dev`; el owner ya dio el OK a este plan).
- [ ] Push `dev` → deploy Railway (automático o manual desde dashboard).
- [ ] Smoke post-deploy contra Railway:
      - `GET /health` → 200
      - `GET /api/events?sport=tennis&league=atp` → torneos
      - `GET /api/events?sport=nba&league=nba` → partidos
      - `GET /api/events` (MMA) → eventos
- [ ] Recompilar APK (`assembleDebug`) con baseUrl Railway + smoke en emulador
      **sin** `adb reverse`: Home con los 3 deportes, navegación completa.

## Fase 6 — Documentación y cierre

- [x] Decidir destino de `memoria/validacion-sesion-fable5-home-winamax.md`
      (raíz del working dir, sin commitear desde Sesión 23): mover a `memoria/`
      y commitear, o borrar. Si hay duda, moverlo a `memoria/` (conservador).
- [ ] Marcar checkboxes de este plan y de `memoria/fases.md` donde aplique.
- [ ] Entrada en `memoria/bitacora.md`.
- [ ] Actualizar `memoria/handoff.md` (estado nuevo + pendientes).
- [ ] Commit final de docs.

---

## Fuera de alcance (pendientes que NO entran en este goal)

- Validación con torneo real de tenis (Mifel Tennis Open) y partido real NBA
  (preseason 2026-10-05) — requieren tiempo real.
- Decisiones de diseño visual global (estilo Winamax en todas las pantallas,
  colores por deporte, fusión Buscar/EventList) — requieren grilling con el owner.
- Faces/headshots ausentes en Home (pendiente Sesión 24 #2).

## Pitfalls conocidos

- LazyColumn: keys compuestas SIEMPRE (`sport-league-id`) — colisiones reales
  vistas en Sesión 24.
- `CompetitionStatus` pydantic usa alias (`displayClock`) — no aplica aquí
  (sin cambios backend), pero no tocar providers.
- Si se recrea el `.venv` en la máquina Windows: reaplicar fix truststore
  (`pip install truststore` + `sitecustomize.py`) — proxy TLS corporativo.
- Backend local para smoke previo al deploy: cwd = raíz del repo, no `src/`.
- Hook pre-commit aborta commits significativos sin tocar `handoff.md` —
  actualizar handoff o `--no-verify` puntual.
