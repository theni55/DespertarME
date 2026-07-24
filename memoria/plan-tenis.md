# Plan: Fase Tenis — ESPN ATP/WTA + integración multi-sport

> Plan por fases con checkboxes para añadir tenis (ATP/WTA) al MVP, replicando el modelo de tarjeta escalonada por pista (court) en vez de matchNumber+1. Rama `feature/tenis`.

## 0. Contexto

- **Objetivo:** replicar el modelo de alertas de MMA para tenis: avisar X min antes de que empiece un partido, siguiendo el partido anterior en la **misma pista**.
- **Diferencia con MMA:** en vez de "combate anterior en la tarjeta" (matchNumber+1) → "partido anterior en la misma pista por fecha dentro del mismo `court`".
- **Fuente:** ESPN Core API (misma API que UFC, sin auth). Verificada en vivo.
- **Rama:** `feature/tenis` desde `dev`.

## 1. Fuente de datos verificada

ESPN Core API tiene tenis con dos ligas (ATP, WTA) y la misma estructura que UFC:

| Endpoint | Respuesta |
|----------|-----------|
| `/v2/sports/tennis/leagues` | 2 ligas: ATP, WTA |
| `/v2/sports/tennis/leagues/{league}/events` | Torneos (`$ref` list) |
| `/v2/sports/tennis/leagues/{league}/events/{id}` | Torneo con `competitions[]` (50-63 partidos) |
| `/v2/sports/tennis/.../competitions/{cId}/status` | `{type: {state}, period}` — **sin `clock`** |

**Estructura por partido:**
- `court.description` → pista (Center Court, Grandstand, Court 1...)
- `competitors[].name` → nombre inline (¡sin necesidad de `AthleteResolver`!)
- `round` → `{description: "Quarterfinal", abbreviation: "QF"}`
- `type.text` → "Men's Singles", "Men's Doubles", etc.
- `format.regulation.periods` → 3 (best-of-3) o 5 (best-of-5)
- `status.$ref` → seguir para obtener `state: pre|in|post` + `period` (nº de set)
- **Sin `matchNumber`** — orden cronológico por `date`

## Decisiones (registradas en `decisiones.md`)

| # | Decisión |
|---|----------|
| D46 | ESPN Core API como fuente de Tenis (ATP+WTA), mismo patrón que UFC |
| D47 | Modelo multi-sport: `sport` field en `BoutSubscription` + `Card`, `previous_bout()` generalizado por pista cuando `court is not None` |
| D48 | Buffer inter-partidos tenis: 15 min (`BUFFER_INTERMATCH_TENNIS_SECONDS=900`) |
| D49 | Tenis: nombres inline del `Competitor.name` (sin `AthleteResolver`) — ESPN tennis sirve el nombre directamente |

## Fases de implementación

### T1 — ESPN Tennis Provider ✅ (nuevo fichero, aislado)

- [ ] `src/app/providers/espn_tennis.py`: `EspnTennisProvider(Provider)` — reutiliza circuit breaker + tenacity de `EspnUfcProvider`
- [ ] DTOs en `providers/models.py`: `Competitor` añade `name: str | None`, `Bout.match_number` default 0, `Bout.court` + `Bout.round`, `TennisCourt`, `TennisRound`
- [ ] `providers/__init__.py`: exportar `EspnTennisProvider`
- [ ] Tests `tests/test_espn_tennis.py` con respx + fixtures grabadas

### T2 — Generalización del dominio ✅ (backward-compatible)

- [ ] `domain/entities.py`: `Bout` añade `court`, `sport`, `round_description`; `Card.previous_bout()` generalizado (court+date si `court is not None`, matchNumber+1 si no); `BoutStatus` añade `sport`
- [ ] `Bout` + `BoutStatus` duration/elapsed properties sport-aware

### T3 — DB model + migración ✅

- [ ] `db/models/subscriptions.py`: columna `sport: str = "mma"`
- [ ] Migración Alembic autogenerada

### T4 — API multi-sport ✅ (?sport= parameter)

- [ ] `config.py`: `espn_tennis_league`, `buffer_intermatch_tennis_seconds`
- [ ] `api/routes/events.py`: provider registry (`dict[str, Provider]`), `?sport=` query param
- [ ] `api/routes/subscriptions.py`: persistir `sport` del body
- [ ] `api/schemas.py`: `BoutOut` (court, sport, round_description), `BoutSubscriptionCreate`/`Out` (sport)
- [ ] Tests actualizados

### T5 — Poller + Scheduler multi-sport ✅

- [ ] `engine/poller.py`: providers dict, agrupar por `(sport, event_id)`, mapeo sport-aware
- [ ] `scheduler.py`: construir dict de providers
- [ ] `main.py`: close de todos los providers

### T6 — Tests ✅

- [ ] Todos los tests verdes (MMA + tenis)
- [ ] `ruff` + `black` + `mypy` limpios

### T7 — App Android

- [ ] `DespertarApi.kt`: `@Query("sport")` en listEvents/getEvent
- [ ] DTOs: `BoutSubscriptionCreate.sport`, `BoutOut.court`/`roundDescription`
- [ ] Home: selector de deporte (tabs MMA / Tenis)
- [ ] EventDetail tenis: agrupado por court, badge round, nombres inline
- [ ] SubscriptionsScreen: badge de deporte

### T8 — Smoke + validación

- [ ] `scripts/probe_tennis.py`
- [ ] Smoke contra ESPN en vivo
- [ ] Android smoke: subscribir a partido de tenis

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Tenis sin `clock` → estimación `in` imprecisa | Branch crítico `post` es exacto; el `in` se refina al terminar el partido |
| 50-63 partidos/torneo vs 12-14 MMA | Un `get_event_card` por torneo/ciclo; solo un status por suscripción activa |
| ESPN reordena partidos día del evento | `previous_bout` se deriva en cada poll (E4) |
| Headshots no disponibles inline | Nombres sí están inline; headshot es nice-to-have no bloqueante |
