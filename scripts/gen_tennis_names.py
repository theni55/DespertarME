"""Genera el mapping _TOURNAMENT_DISPLAY_NAMES para espn_tennis.py.

Fetch de todos los eventos ATP 2026 y WTA 2026 desde ESPN, extrae
tournament_id + location.city, y genera un dict listo para copiar.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx

ESPN_BASE = "https://sports.core.api.espn.com/v2"
SEASONS_PAGES = {"atp": 3, "wta": 5}

# Nombres "hairstyle" para los torneos grandes (se busca por displayName).
# Clave: (league, displayName_substring) -> nombre_deseado
_BIG_TOURNAMENTS: dict[tuple[str, str], str] = {
    ("atp", "Australian Open"): "Australian Open",
    ("atp", "Roland Garros"): "Roland Garros",
    ("atp", "French Open"): "Roland Garros",
    ("atp", "Wimbledon"): "Wimbledon",
    ("atp", "US Open"): "US Open",
    ("atp", "U.s. Open"): "US Open",
    ("wta", "Australian Open"): "Australian Open",
    ("wta", "Roland Garros"): "Roland Garros",
    ("wta", "French Open"): "Roland Garros",
    ("wta", "Wimbledon"): "Wimbledon",
    ("wta", "US Open"): "US Open",
    ("wta", "U.s. Open"): "US Open",
    ("atp", "BNP Paribas Open"): "Indian Wells",
    ("wta", "BNP Paribas Open"): "Indian Wells",
    ("atp", "Miami Open"): "Miami",
    ("wta", "Miami Open"): "Miami",
    ("atp", "Monte Carlo"): "Montecarlo",
    ("atp", "Rolex Monte-Carlo"): "Montecarlo",
    ("atp", "Mutua Madrid"): "Madrid",
    ("wta", "Mutua Madrid"): "Madrid",
    ("atp", "Internazionali BNL"): "Roma",
    ("wta", "Internazionali BNL"): "Roma",
    ("atp", "National Bank Open"): "Canad\u00e1",
    ("wta", "National Bank Open"): "Canad\u00e1",
    ("atp", "Western & Southern"): "Cincinnati",
    ("wta", "Western & Southern"): "Cincinnati",
    ("atp", "Rolex Shanghai"): "Shangh\u00e1i",
    ("atp", "Rolex Paris"): "Par\u00eds",
    ("atp", "Nitto ATP Finals"): "ATP Finals",
    ("wta", "WTA Finals"): "WTA Finals",
    ("atp", "Davis Cup"): "Copa Davis",
    ("atp", "Olympics"): "Juegos Ol\u00edmpicos",
    ("wta", "Olympics"): "Juegos Ol\u00edmpicos",
    ("atp", "Laver Cup"): "Laver Cup",
    ("atp", "United Cup"): "United Cup",
    ("wta", "Billie Jean King Cup"): "Billie Jean King Cup",
}


def _match_big(league: str, display_name: str) -> str | None:
    for (lkey, substr), name in _BIG_TOURNAMENTS.items():
        if lkey == league and substr.lower() in display_name.lower():
            return name
    return None


async def fetch_events(client: httpx.AsyncClient, league: str, pages: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for p in range(1, pages + 1):
        url = (
            f"{ESPN_BASE}/sports/tennis/leagues/{league}"
            f"/seasons/2026/types/2/events?page={p}"
        )
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        season_items = data.get("items") or []
        for item in season_items:
            ref = item.get("$ref", "")
            eid = _event_id_from_ref(ref)
            if eid:
                items.append({"$ref": ref, "event_id": eid})
    return items


_EID_RE = re.compile(r"/events/(\d+-\d+)")


def _event_id_from_ref(ref: str) -> str | None:
    if not ref:
        return None
    m = _EID_RE.search(ref)
    return m.group(1) if m else None


async def fetch_event_detail(
    client: httpx.AsyncClient,
    league: str,
    event_id: str,
    sem: asyncio.Semaphore,
) -> dict[str, Any] | None:
    url = f"{ESPN_BASE}/sports/tennis/leagues/{league}/events/{event_id}"
    async with sem:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None


async def main() -> None:
    sem = asyncio.Semaphore(8)
    async with httpx.AsyncClient(timeout=30.0) as client:
        all_events: list[tuple[str, str]] = []  # (league, event_id)
        for league, pages in SEASONS_PAGES.items():
            events = await fetch_events(client, league, pages)
            for ev in events:
                all_events.append((league, ev["event_id"]))
            print(f"  {league}: {len(events)} eventos en 2026")

        print(f"\n  Total: {len(all_events)} eventos. Fetching detalles...")

        tasks = [
            fetch_event_detail(client, league, eid, sem)
            for league, eid in all_events
        ]
        results = await asyncio.gather(*tasks)

        mapping: dict[str, str] = {}
        seen: set[str] = set()
        for (league, eid), detail in zip(all_events, results):
            if detail is None:
                continue
            tid = eid.split("-")[0]
            display_name = detail.get("name", "") or detail.get("displayName", "")
            location = detail.get("location") or {}
            city = (location.get("city") or "").strip()
            country = (location.get("country") or "").strip()
            circuit = league.upper()

            key = f'(("{league}", "{tid}"))'

            # 1. Nombre hairstyle si es un grande
            big_name = _match_big(league, display_name)
            if big_name:
                mapping[key] = big_name
                seen.add(key)
                continue

            # 2. "{city}" sin circuito (el acordeon ya indica ATP/WTA)
            if city:
                name = city
                mapping[key] = name
                seen.add(key)
                continue

            # 3. fallback: nombre ESPN (ya estamos fetcheando el detalle)
            mapping[key] = display_name
            seen.add(key)

        # Escribir el dict a un fichero (evita problemas de encoding en terminal)
        out_path = "scripts/_tennis_names_output.py"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# Generado automaticamente por scripts/gen_tennis_names.py\n")
            f.write(f"# {len(mapping)} torneos ATP/WTA 2026\n")
            f.write("_TOURNAMENT_DISPLAY_NAMES: dict[tuple[str, str], str] = {\n")
            count = 0
            for key_str, name in sorted(mapping.items()):
                count += 1
                f.write(f'    {key_str}: "{name}",\n')
            f.write("}\n")
        print(f"  Escrito a {out_path}: {count} entries")

        # Debug: mostrar casos donde no coincidio el _match_big
        for (league, eid), detail in zip(all_events, results):
            if detail is None:
                continue
            display_name = detail.get("name", "")
            big = _match_big(league, display_name)
            # Mostrar solo si deberia haber sido un grande pero no hizo match
            if eid.split("-")[0] in ("172", "189", "154", "188"):
                location = detail.get("location") or {}
                city = (location.get("city") or "").strip()
                print(f"  DEBUG id={eid.split('-')[0]} league={league} city={city!r} display={display_name!r} => big={big!r}")


if __name__ == "__main__":
    asyncio.run(main())
