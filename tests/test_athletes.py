"""Tests del AthleteResolver: caché memoria + Redis, degradación en fallos (D32)."""

from __future__ import annotations

from app.providers.athletes import AthleteResolver, ResolvedAthlete
from tests.conftest import FakeProvider


class FailingProvider(FakeProvider):
    async def get_athlete(self, athlete_id: str):  # type: ignore[override]
        self.athlete_calls.append(athlete_id)
        raise RuntimeError("ESPN caído")


async def test_resolve_returns_name_and_headshot(fake_provider) -> None:
    resolver = AthleteResolver(fake_provider)

    athlete = await resolver.resolve("201")

    assert athlete.name == "Conor Test"
    assert athlete.headshot_url is not None
    assert "201" in athlete.headshot_url


async def test_resolve_uses_memory_cache(fake_provider) -> None:
    resolver = AthleteResolver(fake_provider)

    await resolver.resolve("201")
    await resolver.resolve("201")

    assert fake_provider.athlete_calls == ["201"]  # solo 1 fetch real


async def test_resolve_uses_redis_cache_between_resolvers(fake_provider, fake_redis) -> None:
    resolver1 = AthleteResolver(fake_provider, redis_client=fake_redis)
    await resolver1.resolve("201")

    # Resolver nuevo (memoria vacía) → debe salir de Redis, no de la red.
    resolver2 = AthleteResolver(fake_provider, redis_client=fake_redis)
    athlete = await resolver2.resolve("201")

    assert athlete.name == "Conor Test"
    assert fake_provider.athlete_calls == ["201"]


async def test_resolve_degrades_on_provider_failure() -> None:
    provider = FailingProvider()
    resolver = AthleteResolver(provider)

    athlete = await resolver.resolve("999")

    assert athlete == ResolvedAthlete(id="999")
    assert athlete.display == "TBD"


async def test_failed_resolution_is_not_cached() -> None:
    provider = FailingProvider()
    resolver = AthleteResolver(provider)

    await resolver.resolve("999")
    await resolver.resolve("999")

    # Reintenta en cada llamada (no cachea el fallo).
    assert provider.athlete_calls == ["999", "999"]


async def test_resolve_many_dedupes_ids(fake_provider) -> None:
    resolver = AthleteResolver(fake_provider)

    result = await resolver.resolve_many(["101", "102", "101", "", "102"])

    assert set(result.keys()) == {"101", "102"}
    assert sorted(fake_provider.athlete_calls) == ["101", "102"]


async def test_shared_memory_cache_between_resolvers(fake_provider) -> None:
    shared: dict = {}
    resolver1 = AthleteResolver(fake_provider, memory_cache=shared)
    await resolver1.resolve("101")

    resolver2 = AthleteResolver(fake_provider, memory_cache=shared)
    athlete = await resolver2.resolve("101")

    assert athlete.name == "Red Prev"
    assert fake_provider.athlete_calls == ["101"]
