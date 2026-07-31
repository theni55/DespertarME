# Fuentes de datos (investigación)

> Fuentes por deporte, hallazgos verificados de ESPN Core API y tareas de validación pendientes.

## Resumen

| Deporte | Fuente primaria | Auth | ¿Estado en vivo por combate? | Fallback (scraping) |
|---------|----------------|------|-----------------------------|---------------------|
| **MMA — UFC** | **ESPN Core API** `https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc/` | No | **Sí** (state + clock + period por fight) | fuera del MVP (D11) |
| **Tenis — ATP/WTA** | **ESPN Core API** `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{atp\|wta}/` | No | **Sí** (state + period por match, sin clock) | fuera del MVP |
| **MMA — Bellator/PFL** | TheSportsDB (a estudiar cuando se amplíe) | API key gratuita | Limitado | tapology.com |
| **Baloncesto — NBA** | **ESPN Core API** `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/` | No | **Sí** (state + period + clock por partido) | fuera del MVP |
| **Baloncesto — Europa** | API-Basketball (API-Sports) | API key | **Sí** (`status.short` Q1-Q4 + timer) | Sportradar (enterprise) |
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

## APIs de tenis evaluadas — cobertura completa (investigación Sesión 24, 2026-07-27)

Investigación de fuentes alternativas a ESPN para cubrir **todas las
competiciones de tenis** (ATP, WTA, ITF, Challenger, Copa Davis, Grand Slams).

### Comparativa de APIs

| API | Cobertura | Court | Estado | Hora dinámica | Precio |
|-----|-----------|:---:|:---:|:---:|--------|
| ESPN Core API | Solo ATP/WTA | ✅ | ✅ `pre/in/post` | ❌ Fija | Gratis |
| SportScore | ATP/WTA/Davis Cup/ITF | ❌ | ⚠️ texto inline | ❌ Fija | Gratis (atribución) |
| API Tennis | Todas las competiciones | ❌ | ⚠️ texto inline | ❌ Fija | $40-120/mes |
| **Sportradar** | Todas las competiciones | ✅ | ✅ | ✅ `EstimatedStart` | ~$500-5K/mes |
| Stats Perform | Todas las competiciones | ✅ | ✅ | ✅ | ~$1-3K/mes |

### ¿De dónde saca FlashScore los datos?

FlashScore **no recalcula horas con su propio backend**. Usa **Sportradar**
como proveedor de datos. Sportradar expone un campo `startTime.status` con
estos valores para cada partido:

| `status` | Significado | Se actualiza |
|----------|-------------|:---:|
| `StartsAt` | Hora programada oficial del torneo | Fijo |
| `NotBefore` | "No empezará antes de X" (ej. por lluvia) | **Dinámico** |
| `EstimatedStart` | Hora estimada real según progreso del partido anterior en la misma pista | **Dinámico** |
| `FollowsPrevious` | Estimación gruesa: "cuando acabe el anterior en esta pista" | **Dinámico** |
| `NoInformation` | Sin datos de horario | — |

El flujo real de datos es:
```
Supervisor del torneo → feed oficial ATP/WTA → Sportradar/IMG Arena → FlashScore
```

Sportradar adquirió **IMG Arena** (distribuidor oficial de datos ATP/WTA),
consolidando el canal directo desde los torneos.

### ¿Qué significa para DespertarME?

Sportradar ($500-$5K/mes) es la opción correcta para cobertura completa
con hora dinámica, pero su coste solo se justifica si la app escala a
producción con ingresos. El `EstimatorEngine` de DespertarME ya implementa
la misma lógica automáticamente: detecta transiciones `pre→in→post` del
partido anterior en ESPN y recalcula `now + buffer`. La diferencia es un
margen de ~2-3 min extra de imprecisión respecto a un humano en el torneo.

API Tennis ($40/mes) cubre todas las competiciones pero no tiene `court`
ni hora dinámica: misma limitación que ESPN, solo añade cobertura de
torneos ITF/Challenger/Davis Cup. No justifica la migración por sí solo.

## APIs de baloncesto evaluadas (investigación Sesión 24, 2026-07-27)

Investigación de fuentes para baloncesto NBA y ligas europeas. El dato crítico
es el **cuarto actual** (`period`) y el **reloj restante** (`clock`) para
avisar cuándo empieza un cuarto concreto.

### ESPN Core API — Baloncesto

**15 ligas** disponibles, pero la cobertura se limita a NBA, universitaria
y selecciones. **No cubre ligas europeas de clubes** (EuroLeague, ACB, etc.):

```
NBA, WNBA, NCAA masculino, NCAA femenino, FIBA, Olímpico M/F,
NBL (Australia), NBA G-League, Summer Leagues
```

Estructura del status endpoint (verificado en vivo):

```json
GET /basketball/leagues/nba/events/{id}/competitions/{cId}/status
→ {
    "period": 0,           // 0=sin empezar, 1=Q1, 2=Q2, 3=Q3, 4=Q4, 5+=OT
    "clock": 720.0,        // segundos restantes en el cuarto actual
    "displayClock": "12:00",
    "type": {
      "state": "pre"       // "pre" | "in" | "post" (mismo modelo que MMA/Tenis)
    }
  }
```

El endpoint devuelve `state`, `period` y `clock` — compatible con la
arquitectura actual (`Provider` + `EstimatorEngine`). Para baloncesto,
el `EstimatorEngine` detectaría transiciones de `period` en vez de
transiciones de combate/partido: cuando `period` cambia y coincide
con el cuarto objetivo del usuario → push alert.

### Comparativa de APIs

| API | NBA | Europa (EuroLeague/ACB/BBL...) | Period | Clock | Hora dinámica | Precio |
|-----|:---:|:---:|:---:|:---:|:---:|--------|
| ESPN Core API | ✅ | ❌ Solo FIBA/Olímpico | ✅ | ✅ | ❌ | **Gratis** |
| API-Basketball | ✅ | ✅ EuroLeague, ACB, BBL, LNB, Lega A +50 | ✅ | ✅ | ❌ | Free-$40/mes |
| Sportradar | ✅ | ✅ Todas | ✅ | ✅ | ✅ `EstimatedStart` | ~$500-$5K/mes |
| SportScore | ✅ | ✅ | ❌ | ❌ | ❌ | Gratis |

### Diferencia arquitectónica con MMA y Tenis

En MMA el modelo es "combate anterior en la tarjeta" (matchNumber+1), en
tenis es "partido anterior en la misma pista" (court+date). **En baloncesto
es más simple**: los cuartos son secuenciales y fijos (Q1→Q2→Q3→Q4).

El `EstimatorEngine` para baloncesto solo necesita:
1. Leer `period` actual del status endpoint.
2. Cuando `period` cambia y coincide con `target_quarter - 1` en transición
   `in→post` → push alert para el cuarto objetivo.
3. Cushion fijo: ~2 min entre Q1/Q2 y Q3/Q4, ~15 min halftime (Q2→Q3).

No hay que buscar "el partido anterior" — las transiciones son lineales.

### Modelo de alerta para baloncesto

| Suscripción | Disparador |
|-------------|-----------|
| "Avísame al empezar el 2º cuarto" | Fin del Q1 → push |
| "Avísame al empezar el 3er cuarto" | Fin del Q2 (halftime) → push |
| "Avísame al empezar el 4º cuarto" | Fin del Q3 → push |
| "Avísame al empezar el último cuarto" | `period == max_periods-1` y `state == post` → push |

### Conclusión

ESPN gratis cubre NBA con `period` + `clock` + `state` — totalmente viable
para un MVP de baloncesto NBA. API-Basketball ($30-40/mes) añadiría las
ligas europeas (EuroLeague, ACB, BBL, etc.) con el mismo nivel de detalle
de cuarto. Sportradar es la opción enterprise si se necesita hora dinámica
(`EstimatedStart`) y cobertura mundial completa.
