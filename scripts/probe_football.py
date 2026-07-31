"""Smoke test del provider de fútbol contra ESPN en vivo."""

import asyncio

from app.config import settings
from app.providers.espn_football import EspnFootballProvider


async def main() -> None:
    leagues = settings.football_leagues[:3]  # Primeras 3 ligas

    for league in leagues:
        p = EspnFootballProvider(league=league)
        try:
            events = await p.list_upcoming_events()
            print(f"{league}: {len(events)} partidos")
            for e in events[:2]:
                print(f"  {e.id} | {e.name[:60]} | {e.date}")
            if events:
                card = await p.get_event_card(events[0].id)
                print(f"  -> Card: {card.name}, {len(card.bouts)} bouts")
                if card.bouts:
                    b = card.bouts[0]
                    red = b.red_corner
                    blue = b.blue_corner
                    tid = None
                    if red and red.team:
                        tid = red.team.team_id
                    if tid:
                        team = await p.get_team(tid)
                        print(f"  -> Team {tid}: {team.display_name}, logo: {team.logo_url}")
        finally:
            await p.aclose()


if __name__ == "__main__":
    asyncio.run(main())
