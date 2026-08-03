"""Helpers de visibilidad de bouts/comperitors compartidos entre providers y API.

Reglas universales aplicadas a todos los deportes para decidir si un
competidor o bout debe mostrarse o filtrarse (TBD / Bye / placeholders).

Todos los filtros trabajan sobre datos crudos (str | None) para
reutilizarse tanto en los dicts ESPN del provider como en los modelos
Pydantic de la capa API, sin dependencia circular.
"""

from __future__ import annotations

_PLACEHOLDER_NAMES = frozenset({"TBD", "BYE", ""})
_PLACEHOLDER_IDS = frozenset({"0", "2147483647", ""})


def competitor_is_real(name: str | None, cid: str | None) -> bool:
    """True si el competidor NO es un placeholder (TBD, Bye, id sintetico).

    Basta con que tenga nombre real O id real: MMA resuelve via athlete.$ref
    (sin name inline), tenis tiene name inline, y NBA/NFL tienen team.$ref.
    """
    n = (name or "").strip().upper()
    i = str(cid or "").strip()
    name_ok = n not in _PLACEHOLDER_NAMES
    id_ok = i not in _PLACEHOLDER_IDS
    return name_ok or id_ok


def bout_has_real_competitors(
    red_name: str | None,
    red_id: str | None,
    blue_name: str | None,
    blue_id: str | None,
) -> bool:
    """True si AL MENOS un lado del bout tiene un competidor real."""
    return competitor_is_real(red_name, red_id) or competitor_is_real(blue_name, blue_id)
