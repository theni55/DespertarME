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
    (("atp", "10")): "Vienna ATP",
    (("atp", "1001")): "Hangzhou ATP",
    (("atp", "119")): "Doha ATP",
    (("atp", "12")): "Munich ATP",
    (("atp", "129")): "London ATP",
    (("atp", "13")): "Par\u00eds ATP",
    (("atp", "145")): "Houston ATP",
    (("atp", "148")): "Stockholm ATP",
    (("atp", "154")): "Australian Open",
    (("atp", "172")): "Roland Garros",
    (("atp", "188")): "Wimbledon",
    (("atp", "189")): "US Open",
    (("atp", "22")): "Umag ATP",
    (("atp", "23")): "Basel ATP",
    (("atp", "25")): "Dubai ATP",
    (("atp", "27")): "Halle ATP",
    (("atp", "28")): "Marrakech ATP",
    (("atp", "29")): "Montpellier ATP",
    (("atp", "296")): "Delray Beach ATP",
    (("atp", "299")): "Buenos Aires ATP",
    (("atp", "304")): "Kitzb\u00fchel ATP",
    (("atp", "306")): "B\u00e5stad ATP",
    (("atp", "315")): "Shangh\u00e1i ATP",
    (("atp", "338")): "Barcelona ATP",
    (("atp", "339")): "ATP Finals",
    (("atp", "363")): "Winston-Salem ATP",
    (("atp", "375")): "Rio de Janeiro ATP",
    (("atp", "396")): "Geneva ATP",
    (("atp", "4")): "Rotterdam ATP",
    (("atp", "400")): "Estoril ATP",
    (("atp", "411")): "Indian Wells ATP",
    (("atp", "413")): "Madrid ATP",
    (("atp", "414")): "Roma ATP",
    (("atp", "415")): "'s-Hertogenbosch ATP",
    (("atp", "42")): "Montecarlo ATP",
    (("atp", "421")): "Canad\u00e1 ATP",
    (("atp", "424")): "Los Cabos ATP",
    (("atp", "440")): "Brussels ATP",
    (("atp", "441")): "Chengdu ATP",
    (("atp", "444")): "Eastbourne ATP",
    (("atp", "452")): "Lyon ATP",
    (("atp", "49")): "Stuttgart ATP",
    (("atp", "5")): "Tokyo ATP",
    (("atp", "611")): "Adelaide ATP",
    (("atp", "620")): "Santiago ATP",
    (("atp", "637")): "Mallorca ATP",
    (("atp", "7")): "Gstaad ATP",
    (("atp", "708")): "Almaty ATP",
    (("atp", "711")): "Acapulco ATP",
    (("atp", "713")): "Miami ATP",
    (("atp", "718")): "Cincinnati ATP",
    (("atp", "836")): "Dallas ATP",
    (("atp", "865")): "Jeddah ATP",
    (("atp", "888")): "Washington ATP",
    (("atp", "925")): "Auckland ATP",
    (("atp", "942")): "Hamburg ATP",
    (("atp", "959")): "Beijing ATP",
    (("atp", "970")): "Brisbane ATP",
    (("atp", "971")): "Bank of China Hong Kong Tennis Open",
    (("atp", "974")): "Bucharest ATP",
    (("wta", "1002")): "Hamburg WTA",
    (("wta", "1005")): "S\u00e3o Paulo WTA",
    (("wta", "1007")): "Cali WTA",
    (("wta", "1009")): "Singapore WTA",
    (("wta", "1012")): "Antalya WTA",
    (("wta", "1013")): "Antalya WTA",
    (("wta", "1015")): "Ilkley WTA",
    (("wta", "1017")): "Rome WTA",
    (("wta", "1018")): "Newport WTA",
    (("wta", "1019")): "Tolentino WTA",
    (("wta", "1020")): "Mallorca WTA",
    (("wta", "1022")): "Porto WTA",
    (("wta", "1024")): "Caldas da Rainha WTA",
    (("wta", "1025")): "Rovereto WTA",
    (("wta", "1027")): "Huzhou WTA",
    (("wta", "1028")): "Jingshan WTA",
    (("wta", "1029")): "Suzhou WTA",
    (("wta", "1031")): "Austin WTA",
    (("wta", "1034")): "Santiago de Quer\u00e9taro WTA",
    (("wta", "1036")): "Samsun WTA",
    (("wta", "1037")): "Rio de Janeiro WTA",
    (("wta", "1053")): "Ostrava WTA",
    (("wta", "1055")): "Manila WTA",
    (("wta", "1056")): "Oeiras WTA",
    (("wta", "1057")): "Oeiras WTA",
    (("wta", "1058")): "Dubrovnik WTA",
    (("wta", "1059")): "Les Sables d'Olonne WTA",
    (("wta", "1061")): "Oeiras WTA",
    (("wta", "1062")): "Istanbul WTA",
    (("wta", "1063")): "Austin WTA",
    (("wta", "1064")): "Madrid WTA",
    (("wta", "1065")): "Brescia WTA",
    (("wta", "1066")): "Modena WTA",
    (("wta", "1067")): "Memphis WTA",
    (("wta", "1069")): "Athens WTA",
    (("wta", "1070")): "Figueira Da Foz WTA",
    (("wta", "1071")): "Istanbul WTA",
    (("wta", "1072")): "Kitzb\u00fchel WTA",
    (("wta", "1073")): "T\u00e2rgu Mure\u0219 WTA",
    (("wta", "1075")): "Philadelphia WTA",
    (("wta", "1076")): "Antalya WTA",
    (("wta", "1077")): "Ankara WTA",
    (("wta", "1078")): "Adana WTA",
    (("wta", "1079")): "Lisboa WTA",
    (("wta", "1080")): "Curitiba WTA",
    (("wta", "1081")): "Courmayeur WTA",
    (("wta", "1082")): "Luanda WTA",
    (("wta", "1083")): "Miami WTA",
    (("wta", "154")): "Australian Open",
    (("wta", "172")): "Roland Garros",
    (("wta", "188")): "Wimbledon",
    (("wta", "189")): "US Open",
    (("wta", "199")): "Linz WTA",
    (("wta", "227")): "Birmingham WTA",
    (("wta", "228")): "Charleston WTA",
    (("wta", "231")): "Rabat WTA",
    (("wta", "232")): "Guangzhou WTA",
    (("wta", "237")): "Strasbourg WTA",
    (("wta", "245")): "Hobart WTA",
    (("wta", "25")): "Dubai WTA",
    (("wta", "254")): "Stuttgart WTA",
    (("wta", "256")): "Doha WTA",
    (("wta", "264")): "Tokyo WTA",
    (("wta", "306")): "B\u00e5stad WTA",
    (("wta", "341")): "Monterrey WTA",
    (("wta", "345")): "Osaka WTA",
    (("wta", "380")): "Prudential Hong Kong Tennis Open",
    (("wta", "381")): "Wuhan WTA",
    (("wta", "382")): "WTA Finals",
    (("wta", "401")): "Prague WTA",
    (("wta", "411")): "Indian Wells WTA",
    (("wta", "413")): "Madrid WTA",
    (("wta", "414")): "Roma WTA",
    (("wta", "415")): "'s-Hertogenbosch WTA",
    (("wta", "421")): "Canad\u00e1 WTA",
    (("wta", "423")): "Jiangxi WTA",
    (("wta", "444")): "Eastbourne WTA",
    (("wta", "503")): "Mumbai WTA",
    (("wta", "524")): "Bogot\u00e1 WTA",
    (("wta", "525")): "Palermo WTA",
    (("wta", "611")): "Adelaide WTA",
    (("wta", "635")): "Berlin WTA",
    (("wta", "636")): "Bad Homburg WTA",
    (("wta", "713")): "Miami WTA",
    (("wta", "718")): "Cincinnati WTA",
    (("wta", "770")): "Saint Malo WTA",
    (("wta", "786")): "Ljubljana WTA",
    (("wta", "793")): "Cluj-Napoca WTA",
    (("wta", "795")): "Midland WTA",
    (("wta", "811")): "Seoul WTA",
    (("wta", "864")): "Makarska WTA",
    (("wta", "866")): "Nottingham WTA",
    (("wta", "870")): "Paris WTA",
    (("wta", "871")): "Valencia WTA",
    (("wta", "873")): "Contrexeville WTA",
    (("wta", "874")): "Iasi WTA",
    (("wta", "875")): "Vancouver WTA",
    (("wta", "887")): "Guadalajara WTA",
    (("wta", "888")): "Washington WTA",
    (("wta", "889")): "Chennai WTA",
    (("wta", "896")): "Parma WTA",
    (("wta", "897")): "Foggia WTA",
    (("wta", "900")): "Rouen WTA",
    (("wta", "908")): "Austin WTA",
    (("wta", "911")): "M\u00e9rida WTA",
    (("wta", "925")): "Auckland WTA",
    (("wta", "930")): "Abu Dhabi WTA",
    (("wta", "947")): "La Bisbal d'Empord\u00e0 WTA",
    (("wta", "959")): "Beijing WTA",
    (("wta", "961")): "Warsaw WTA",
    (("wta", "963")): "Ningbo WTA",
    (("wta", "964")): "Barranquilla WTA",
    (("wta", "970")): "Brisbane WTA",
    (("wta", "976")): "Antalya WTA",
    (("wta", "977")): "Puerto Vallarta WTA",
    (("wta", "979")): "Canberra WTA",
    (("wta", "995")): "Oeiras WTA",
    (("wta", "997")): "London WTA",
    (("wta", "998")): "Montreux WTA",
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

        async def _fetch_summary(eid: str) -> EventSummary | None:
            url = self._url(f"/sports/tennis/leagues/{self._league}/events/{eid}")
            async with sem:
                try:
                    ev_data = await self._request(url)
                except Exception:
                    logger.warning("No se pudo cargar resumen del torneo %s", eid)
                    return None
            ev_status = (ev_data.get("status") or {}).get("type") or {}
            if ev_status.get("state") == "post":
                return None
            tournament_id = ev_data["id"].split("-")[0]
            key = (self._league, tournament_id)
            name = _TOURNAMENT_DISPLAY_NAMES.get(key, ev_data.get("name", ""))
            return EventSummary(
                id=ev_data["id"],
                name=name,
                date=ev_data.get("date", ""),
            )

        raw_summaries = await asyncio.gather(*(_fetch_summary(eid) for eid in ids))
        summaries = [s for s in raw_summaries if s is not None]

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
