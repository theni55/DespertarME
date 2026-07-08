"""Smoke manual del provider ESPN UFC.

Lanza una secuencia real contra ESPN Core API (sin mocks) y muestra:
- Próximo evento (id, nombre, fecha).
- Número de combates y segmentos de la tarjeta.
- Estado del primer combate (pre/in/post).

Uso:
    python scripts/probe_espn.py

Requiere red (no necesita BD/Redis). Si ESPN no responde, tenacity reintenta y
el circuit breaker puede abrir; en tal caso se verá en la salida.
"""

from __future__ import annotations

import asyncio
import sys

from app.providers import CircuitBreakerOpenError, EspnUfcProvider


async def main() -> int:
    print("=== Probe ESPN UFC (smoke manual) ===\n")
    async with EspnUfcProvider() as provider:
        try:
            summaries = await provider.list_upcoming_events()
        except CircuitBreakerOpenError as exc:
            print(f"Circuit breaker abierto: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"Error listando eventos: {exc!r}", file=sys.stderr)
            return 1

        if not summaries:
            print("No hay eventos próximos.")
            return 0

        print(f"Eventos próximos ({len(summaries)}):")
        for s in summaries:
            print(f"  - {s.id} | {s.name} | {s.date}")
        print()

        next_event = summaries[0]
        print(f"=== Tarjeta de '{next_event.name}' ({next_event.id}) ===\n")
        try:
            event = await provider.get_event_card(next_event.id)
        except Exception as exc:
            print(f"Error obteniendo tarjeta: {exc!r}", file=sys.stderr)
            return 1

        print(f"Combates: {len(event.bouts)}")
        segments: dict[str, int] = {}
        for bout in event.bouts:
            seg = bout.card_segment.name if bout.card_segment else "?"
            segments[seg] = segments.get(seg, 0) + 1
        print(f"Por segmento: {segments}\n")

        print("Combates (ordenados por matchNumber descendente):")
        for bout in sorted(event.bouts, key=lambda b: b.match_number, reverse=True):
            red = bout.red_corner
            blue = bout.blue_corner
            red_id = red.id if red else "-"
            blue_id = blue.id if blue else "-"
            wc = bout.weight_class.text if bout.weight_class else "?"
            seg = bout.card_segment.name if bout.card_segment else "?"
            print(
                f"  #{bout.match_number:2d} [{seg:8s}] {wc:20s} " f"red={red_id} vs blue={blue_id}"
            )

        first = event.bouts[0]
        print(f"\n=== Estado del primer combate (id={first.id}) ===")
        try:
            status = await provider.get_competition_status(next_event.id, first.id)
        except Exception as exc:
            print(f"Error obteniendo status: {exc!r}", file=sys.stderr)
            return 1

        print(f"  state     = {status.type.state}")
        print(f"  completed = {status.type.completed}")
        print(f"  period    = {status.period}")
        print(f"  clock     = {status.clock}")
        print(f"  detail    = {status.type.short_detail or status.type.description}")

    print("\n=== Probe OK ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
