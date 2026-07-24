"""Smoke manual del provider ESPN Tenis (D46).

Ejecuta contra la API real para verificar conectividad, parseo de torneos,
partidos con pista y estado de competicion.

Uso:
    python scripts/probe_tennis.py
    python scripts/probe_tennis.py --league wta
"""

from __future__ import annotations

import argparse
import asyncio

from app.providers.espn_tennis import EspnTennisProvider


async def main(league: str = "atp") -> None:
    print(f"=== Probe ESPN Tenis ({league.upper()}) ===\n")

    async with EspnTennisProvider(league=league) as provider:
        # 1. Listar torneos
        print("1. Listando torneos...")
        events = await provider.list_upcoming_events()
        print(f"   OK: {len(events)} torneos encontrados")
        for ev in events[:5]:
            print(f"   - {ev.name} ({ev.id}) — {ev.date}")
        print()

        if not events:
            print("   Sin torneos activos. Abortando.")
            return

        event = events[0]
        print(f"2. Cargando torneo: {event.name} ({event.id})")

        card = await provider.get_event_card(event.id)
        print(f"   OK: {len(card.bouts)} partidos")
        print(f"   Pistas: {sorted(set(b.court.description for b in card.bouts if b.court))}")
        print()

        # Mostrar muestra: primeros 3 partidos
        for bout in card.bouts[:3]:
            players = []
            for c in bout.competitors:
                players.append(c.name or f"id={c.id}")
            court = bout.court.description if bout.court else "sin pista"
            ronda = bout.round.description if bout.round else "sin ronda"
            print(f"   - [{court}] {ronda}: {' vs '.join(players)} ({bout.date})")

        # 3. Status de un partido
        first_bout = card.bouts[0]
        print(f"\n3. Status del primer partido: {first_bout.id}")
        status = await provider.get_competition_status(event.id, first_bout.id)
        print(f"   Estado: {status.type.state}, period: {status.period}, completed: {status.type.completed}")

        # 4. Atleta (si hay competitor con athlete $ref)
        first_comp = first_bout.competitors[0] if first_bout.competitors else None
        if first_comp and first_comp.athlete and first_comp.athlete.athlete_id:
            aid = first_comp.athlete.athlete_id
            print(f"\n4. Resolviendo atleta {aid}...")
            athlete = await provider.get_athlete(aid)
            print(f"   Name: {athlete.display_name}")
            print(f"   Headshot: {athlete.headshot_url}")

    print("\n=== Probe completado ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke manual del provider ESPN Tenis")
    parser.add_argument("--league", default="atp", choices=["atp", "wta"], help="Liga (default: atp)")
    args = parser.parse_args()
    asyncio.run(main(league=args.league))
