# Fuentes de datos (investigación)

> Fuentes por deporte, hallazgos verificados de ESPN Core API y tareas de validación pendientes.

## Resumen

| Deporte | Fuente primaria | Auth | ¿Estado en vivo por combate? | Fallback (scraping) |
|---------|----------------|------|-----------------------------|---------------------|
| **MMA — UFC** | **ESPN Core API** `https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc/` | No | **Sí** (state + clock + period por fight) | fuera del MVP (D11) |
| **MMA — Bellator/PFL** | TheSportsDB (a estudiar cuando se amplíe) | API key gratuita | Limitado | tapology.com |
| **Boxeo** | (fuera del MVP) | — | — | — |
| **Tenis ATP/WTA** | (fuera del MVP) | — | No | flashscore.es / tennistemple.com |

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

## Tareas pendientes de validación (Fase 0)

- [ ] Confirmar campos de atleta (`/athletes/{id}`) para mostrar nombre en alerta.
- [ ] Validar behavior del status endpoint durante combate en vivo (cuando `state:"in"`).
