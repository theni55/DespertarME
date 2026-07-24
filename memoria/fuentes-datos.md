# Fuentes de datos (investigación)

> Fuentes por deporte, hallazgos verificados de ESPN Core API y tareas de validación pendientes.

## Resumen

| Deporte | Fuente primaria | Auth | ¿Estado en vivo por combate? | Fallback (scraping) |
|---------|----------------|------|-----------------------------|---------------------|
| **MMA — UFC** | **ESPN Core API** `https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc/` | No | **Sí** (state + clock + period por fight) | fuera del MVP (D11) |
| **Tenis — ATP/WTA** | **ESPN Core API** `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{atp\|wta}/` | No | **Sí** (state + period por match, sin clock) | fuera del MVP |
| **MMA — Bellator/PFL** | TheSportsDB (a estudiar cuando se amplíe) | API key gratuita | Limitado | tapology.com |
| **Boxeo** | (fuera del MVP) | — | — | — |

## Hallazgos ESPN verificados en vivo (Sesión 2)

- **Evento de prueba**: UFC 329 *McGregor vs Holloway 2* (11 jul 2026) → devolvió **14 combates** con tarjeta completa.
- Endpoints:
  - `GET /events?seasontype=2` → lista eventos de la temporada.
  - `GET /events/{eventId}` → evento + array `competitions[]` con todos los combates.
  - `GET /events/{eventId}/competitions/{competitionId}/status` → `{clock, period, type:{state:"pre"|"in"|"post", completed}}`.
- **Campos clave por combate** (todos presentes y verificados):
  - `matchNumber` (1–14) → **orden explícito**, 1 = main event ⭐
  - `cardSegment.name` → "main" / "prelims1" / "prelims2"
  - `date` / `endDate` por combate
  - `format.regulation.periods` → 3 o 5 rounds
  - `format.regulation.clock` → 300 seg/round
  - `competitors[].order` (1=red, 2=blue), `winner`, `athlete $ref`

## Notas

- ESPN no requiere auth, pero respeta rate-limit implícito; usar `httpx` con
  backoff exponencial con jitter (D20).
- ESPN Core API es la fuente que usa el propio ESPN.com; alta fiabilidad.
- TheSportsDB queda reservado para Bellator/PFL (D12), fuera del MVP actual.

## Hallazgos Tenis verificados en vivo (Sesión 23)

- **Torneo de prueba**: ATP Generali Open Kitzbuhel (304-2026) → 54 partidos, 3 pistas (Center Court, Grandstand, Küchenmeister).
- **Endpoints**:
  - `GET /events?seasontype=2` → lista de torneos ($ref).
  - `GET /events/{eventId}` → torneo completo con `competitions[]` (50-63 partidos).
  - `GET /events/{eventId}/competitions/{competitionId}/status` → `{type:{state:"pre"|"in"|"post", completed}, period}`. **Sin `clock`** (a diferencia de MMA).
- **Campos clave por partido**:
  - `court.description` → "Center Court", "Grandstand", "Court 1"...
  - `competitors[].name` → nombre del jugador inline (no requiere fetch a `/athletes/{id}` como en MMA)
  - `round.roundType` + `round.description` + `round.abbreviation` → ronda (QF, SF, Final, 1ST...)
  - `type.text` → "Men's Singles", "Men's Doubles", etc.
  - `format.regulation.periods` → 3 (best-of-3) o 5 (best-of-5)
  - **Sin `matchNumber`** — el orden es cronológico por `date` dentro de cada pista.
- **Leagues disponibles**: ATP (`atp`), WTA (`wta`).

## Tareas pendientes de validación (Fase 0)

- [ ] Confirmar campos de atleta (`/athletes/{id}`) para mostrar nombre en alerta.
  **Estado (Sesión 4):** los `competitors[].athlete` del event detail vienen como
  `$ref` (URL), no inline. Habrá que seguir la ref para obtener el nombre del
  atleta cuando se necesite en el mensaje de la llamada (Fase 5) o en el admin
  web (Fase 3). No bloquea Fase 2.
- [x] Validar behavior del status endpoint durante combate en vivo (cuando `state:"in"`).
  **Estado (Sesión 4):** no había eventos `in`/`post` en la temporada 2026 al
  grabar (solo UFC 329 con 14 combates en `pre`). Se sintetizaron fixtures
  `competition_status_in.json` y `_post.json` a partir del esquema verificado
  del `pre` real. Validación en vivo queda pendiente para cuando haya un
  combate en curso.
