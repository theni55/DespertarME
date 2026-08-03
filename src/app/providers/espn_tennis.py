"""Provider de ESPN Core API para Tenis ATP/WTA (D46).

Endpoints (verificados en vivo, Sesion 23):
- `GET /sports/tennis/leagues/{league}/events?seasontype=2` -> lista de torneos.
- `GET /sports/tennis/leagues/{league}/events/{id}` -> torneo completo.
- `GET /sports/tennis/leagues/{league}/events/{id}/competitions/{cId}/status`
  -> `{period, type:{state:"pre"|"in"|"post", completed}}` (sin `clock`).

Resiliencia (D20): heredada de `_EspnBaseProvider`.

Diferencias clave con MMA (D49):
- Nombres de jugadores inline en `competitors[].name` -> no requiere AthleteResolver.
- Sin `matchNumber` -> orden por `date` dentro de cada `court`.
- Sin `clock` en status -> solo `period` (numero de set).
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.providers._base_provider import _EspnBaseProvider
from app.providers._visibility import bout_has_real_competitors
from app.providers.models import AthleteDetail, CompetitionStatus, Event, EventSummary

logger = logging.getLogger(__name__)

_EVENT_ID_RE = re.compile(r"/events/(\d+-\d+|\d+)")


def _event_id_from_ref(ref: str) -> str | None:
    if not ref:
        return None
    path = urlparse(ref).path
    m = _EVENT_ID_RE.search(path)
    return m.group(1) if m else None


def _parse_event_date(raw: str) -> datetime:
    value = raw
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


# Nombres "comunes" de torneos ATP/WTA 2026 (generado via scripts/gen_tennis_names.py).
# Clave: (league, tournament_id). Si un torneo no esta aqui, se usa el nombre de ESPN.
_TOURNAMENT_DISPLAY_NAMES: dict[tuple[str, str], str] = {
    (("atp", "10")): "Vienna",
    (("atp", "1001")): "Hangzhou",
    (("atp", "119")): "Doha",
    (("atp", "12")): "Munich",
    (("atp", "129")): "London",
    (("atp", "13")): "París",
    (("atp", "145")): "Houston",
    (("atp", "148")): "Stockholm",
    (("atp", "154")): "Australian Open",
    (("atp", "172")): "Roland Garros",
    (("atp", "188")): "Wimbledon",
    (("atp", "189")): "US Open",
    (("atp", "22")): "Umag",
    (("atp", "23")): "Basel",
    (("atp", "25")): "Dubai",
    (("atp", "27")): "Halle",
    (("atp", "28")): "Marrakech",
    (("atp", "29")): "Montpellier",
    (("atp", "296")): "Delray Beach",
    (("atp", "299")): "Buenos Aires",
    (("atp", "304")): "Kitzbühel",
    (("atp", "306")): "Båstad",
    (("atp", "315")): "Shanghái",
    (("atp", "338")): "Barcelona",
    (("atp", "339")): "ATP Finals",
    (("atp", "363")): "Winston-Salem",
    (("atp", "375")): "Rio de Janeiro",
    (("atp", "396")): "Geneva",
    (("atp", "4")): "Rotterdam",
    (("atp", "400")): "Estoril",
    (("atp", "411")): "Indian Wells",
    (("atp", "413")): "Madrid",
    (("atp", "414")): "Roma",
    (("atp", "415")): "'s-Hertogenbosch",
    (("atp", "42")): "Montecarlo",
    (("atp", "421")): "Canadá",
    (("atp", "424")): "Los Cabos",
    (("atp", "440")): "Brussels",
    (("atp", "441")): "Chengdu",
    (("atp", "444")): "Eastbourne",
    (("atp", "452")): "Lyon",
    (("atp", "49")): "Stuttgart",
    (("atp", "5")): "Tokyo",
    (("atp", "611")): "Adelaide",
    (("atp", "620")): "Santiago",
    (("atp", "637")): "Mallorca",
    (("atp", "7")): "Gstaad",
    (("atp", "708")): "Almaty",
    (("atp", "711")): "Acapulco",
    (("atp", "713")): "Miami",
    (("atp", "718")): "Cincinnati",
    (("atp", "836")): "Dallas",
    (("atp", "865")): "Jeddah",
    (("atp", "888")): "Washington",
    (("atp", "925")): "Auckland",
    (("atp", "942")): "Hamburg",
    (("atp", "959")): "Beijing",
    (("atp", "970")): "Brisbane",
    (("atp", "971")): "Bank of China Hong Kong Tennis Open",
    (("atp", "974")): "Bucharest",
    (("wta", "1002")): "Hamburg",
    (("wta", "1005")): "São Paulo",
    (("wta", "1007")): "Cali",
    (("wta", "1009")): "Singapore",
    (("wta", "1012")): "Antalya",
    (("wta", "1013")): "Antalya",
    (("wta", "1015")): "Ilkley",
    (("wta", "1017")): "Rome",
    (("wta", "1018")): "Newport",
    (("wta", "1019")): "Tolentino",
    (("wta", "1020")): "Mallorca",
    (("wta", "1022")): "Porto",
    (("wta", "1024")): "Caldas da Rainha",
    (("wta", "1025")): "Rovereto",
    (("wta", "1027")): "Huzhou",
    (("wta", "1028")): "Jingshan",
    (("wta", "1029")): "Suzhou",
    (("wta", "1031")): "Austin",
    (("wta", "1034")): "Santiago de Querétaro",
    (("wta", "1036")): "Samsun",
    (("wta", "1037")): "Rio de Janeiro",
    (("wta", "1053")): "Ostrava",
    (("wta", "1055")): "Manila",
    (("wta", "1056")): "Oeiras",
    (("wta", "1057")): "Oeiras",
    (("wta", "1058")): "Dubrovnik",
    (("wta", "1059")): "Les Sables d'Olonne",
    (("wta", "1061")): "Oeiras",
    (("wta", "1062")): "Istanbul",
    (("wta", "1063")): "Austin",
    (("wta", "1064")): "Madrid",
    (("wta", "1065")): "Brescia",
    (("wta", "1066")): "Modena",
    (("wta", "1067")): "Memphis",
    (("wta", "1069")): "Athens",
    (("wta", "1070")): "Figueira Da Foz",
    (("wta", "1071")): "Istanbul",
    (("wta", "1072")): "Kitzbühel",
    (("wta", "1073")): "Târgu Mureș",
    (("wta", "1075")): "Philadelphia",
    (("wta", "1076")): "Antalya",
    (("wta", "1077")): "Ankara",
    (("wta", "1078")): "Adana",
    (("wta", "1079")): "Lisboa",
    (("wta", "1080")): "Curitiba",
    (("wta", "1081")): "Courmayeur",
    (("wta", "1082")): "Luanda",
    (("wta", "1083")): "Miami",
    (("wta", "154")): "Australian Open",
    (("wta", "172")): "Roland Garros",
    (("wta", "188")): "Wimbledon",
    (("wta", "189")): "US Open",
    (("wta", "199")): "Linz",
    (("wta", "227")): "Birmingham",
    (("wta", "228")): "Charleston",
    (("wta", "231")): "Rabat",
    (("wta", "232")): "Guangzhou",
    (("wta", "237")): "Strasbourg",
    (("wta", "245")): "Hobart",
    (("wta", "25")): "Dubai",
    (("wta", "254")): "Stuttgart",
    (("wta", "256")): "Doha",
    (("wta", "264")): "Tokyo",
    (("wta", "306")): "Båstad",
    (("wta", "341")): "Monterrey",
    (("wta", "345")): "Osaka",
    (("wta", "380")): "Prudential Hong Kong Tennis Open",
    (("wta", "381")): "Wuhan",
    (("wta", "382")): "WTA Finals",
    (("wta", "401")): "Prague",
    (("wta", "411")): "Indian Wells",
    (("wta", "413")): "Madrid",
    (("wta", "414")): "Roma",
    (("wta", "415")): "'s-Hertogenbosch",
    (("wta", "421")): "Canadá",
    (("wta", "423")): "Jiangxi",
    (("wta", "444")): "Eastbourne",
    (("wta", "503")): "Mumbai",
    (("wta", "524")): "Bogotá",
    (("wta", "525")): "Palermo",
    (("wta", "611")): "Adelaide",
    (("wta", "635")): "Berlin",
    (("wta", "636")): "Bad Homburg",
    (("wta", "713")): "Miami",
    (("wta", "718")): "Cincinnati",
    (("wta", "770")): "Saint Malo",
    (("wta", "786")): "Ljubljana",
    (("wta", "793")): "Cluj-Napoca",
    (("wta", "795")): "Midland",
    (("wta", "811")): "Seoul",
    (("wta", "864")): "Makarska",
    (("wta", "866")): "Nottingham",
    (("wta", "870")): "Paris",
    (("wta", "871")): "Valencia",
    (("wta", "873")): "Contrexeville",
    (("wta", "874")): "Iasi",
    (("wta", "875")): "Vancouver",
    (("wta", "887")): "Guadalajara",
    (("wta", "888")): "Washington",
    (("wta", "889")): "Chennai",
    (("wta", "896")): "Parma",
    (("wta", "897")): "Foggia",
    (("wta", "900")): "Rouen",
    (("wta", "908")): "Austin",
    (("wta", "911")): "Mérida",
    (("wta", "925")): "Auckland",
    (("wta", "930")): "Abu Dhabi",
    (("wta", "947")): "La Bisbal d'Empordà",
    (("wta", "959")): "Beijing",
    (("wta", "961")): "Warsaw",
    (("wta", "963")): "Ningbo",
    (("wta", "964")): "Barranquilla",
    (("wta", "970")): "Brisbane",
    (("wta", "976")): "Antalya",
    (("wta", "977")): "Puerto Vallarta",
    (("wta", "979")): "Canberra",
    (("wta", "995")): "Oeiras",
    (("wta", "997")): "London",
    (("wta", "998")): "Montreux",
}


class EspnTennisProvider(_EspnBaseProvider):
    """Provider concreto para ESPN Core API (Tenis ATP/WTA)."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        league: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        cb_fails: int | None = None,
        cb_open_seconds: float | None = None,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            league=league or settings.espn_tennis_league,
            timeout=timeout,
            max_retries=max_retries,
            cb_fails=cb_fails,
            cb_open_seconds=cb_open_seconds,
            client=client,
            clock=clock,
        )

    # --- Provider ABC ----------------------------------------------------

    async def list_upcoming_events(
        self, *, min_date: datetime | None = None, max_concurrent: int = 4
    ) -> Sequence[EventSummary]:
        list_url = self._url(f"/sports/tennis/leagues/{self._league}/events?seasontype=2")
        data = await self._request(list_url)
        ids: list[str] = []
        for item in data.get("items", []):
            ref = item.get("$ref", "")
            eid = _event_id_from_ref(ref)
            if eid:
                ids.append(eid)

        sem = asyncio.Semaphore(max_concurrent)

        async def _fetch_summary(eid: str) -> list[EventSummary]:
            url = self._url(f"/sports/tennis/leagues/{self._league}/events/{eid}")
            async with sem:
                try:
                    ev_data = await self._request(url)
                except Exception:
                    logger.warning("No se pudo cargar resumen del torneo %s", eid)
                    return []
            ev_status = (ev_data.get("status") or {}).get("type") or {}
            if ev_status.get("state") == "post":
                return []
            tournament_id = ev_data["id"].split("-")[0]
            key = (self._league, tournament_id)
            name = _TOURNAMENT_DISPLAY_NAMES.get(key, ev_data.get("name", ""))

            # Detectar singles vs doubles y devolver entradas separadas.
            competitions = ev_data.get("competitions") or []
            has_singles = any(
                "Singles" in ((c.get("type") or {}).get("text") or "") for c in competitions
            )
            has_doubles = any(
                "Doubles" in ((c.get("type") or {}).get("text") or "") for c in competitions
            )

            def _has_alive_bout(mode: str) -> bool:
                """True si hay AL MENOS un bout del tipo indicado con competidores
                reales y sin winner (datos inline, 0 llamadas extra a ESPN)."""
                for c in competitions:
                    if mode not in ((c.get("type") or {}).get("text") or ""):
                        continue
                    competitors = c.get("competitors") or []
                    if len(competitors) >= 2:
                        r = competitors[0]
                        b = competitors[1]
                        if bout_has_real_competitors(
                            r.get("name"),
                            str(r.get("id", "")),
                            b.get("name"),
                            str(b.get("id", "")),
                        ) and not (r.get("winner") or b.get("winner")):
                            return True
                    elif len(competitors) == 1:
                        comp = competitors[0]
                        if bout_has_real_competitors(
                            comp.get("name"), str(comp.get("id", "")), None, None
                        ) and not comp.get("winner"):
                            return True
                return False

            result: list[EventSummary] = []
            if has_singles and _has_alive_bout("Singles"):
                result.append(
                    EventSummary(
                        id=ev_data["id"],
                        name=name,
                        date=ev_data.get("date", ""),
                    )
                )
            if has_doubles and _has_alive_bout("Doubles"):
                result.append(
                    EventSummary(
                        id=ev_data["id"] + "_doubles",
                        name=f"{name} Dobles",
                        date=ev_data.get("date", ""),
                    )
                )
            if not result:
                result.append(
                    EventSummary(
                        id=ev_data["id"],
                        name=name,
                        date=ev_data.get("date", ""),
                    )
                )
            return result

        raw_summaries = await asyncio.gather(*(_fetch_summary(eid) for eid in ids))
        summaries = [s for sublist in raw_summaries if sublist for s in sublist]

        cutoff = min_date or datetime.now(UTC)
        min_cutoff = datetime.now(UTC) - timedelta(days=14)
        if cutoff > min_cutoff:
            cutoff = min_cutoff
        upcoming: list[EventSummary] = []
        for s in summaries:
            try:
                ev_dt = _parse_event_date(s.date)
            except ValueError:
                logger.warning("Fecha invalida en torneo %s: %s", s.id, s.date)
                continue
            if ev_dt >= cutoff:
                upcoming.append(s)
        upcoming.sort(key=lambda x: x.date)
        return upcoming

    async def get_event_card(self, event_id: str) -> Event:
        url = self._url(f"/sports/tennis/leagues/{self._league}/events/{event_id}")
        data = await self._request(url)
        return Event.model_validate(data)

    async def get_competition_status(self, event_id: str, competition_id: str) -> CompetitionStatus:
        url = self._url(
            f"/sports/tennis/leagues/{self._league}/events/{event_id}"
            f"/competitions/{competition_id}/status"
        )
        data = await self._request(url)
        return CompetitionStatus.model_validate(data)

    async def get_athlete(self, athlete_id: str) -> AthleteDetail:
        url = self._url(f"/sports/tennis/athletes/{athlete_id}")
        data = await self._request(url)
        return AthleteDetail.model_validate(data)
