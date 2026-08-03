"""Tests unitarios del modulo de visibilidad de bouts (D78).

Verifica que `competitor_is_real` y `bout_has_real_competitors` reconocen
correctamente placeholders (TBD/Bye/id sintetico) en todos los deportes.
"""

from __future__ import annotations

import pytest

from app.providers._visibility import bout_has_real_competitors, competitor_is_real


class TestCompetitorIsReal:
    @pytest.mark.parametrize(
        "name,cid,expected",
        [
            ("Roger Federer", "12345", True),  # jugador real con id real
            ("TBD", "2147483647", False),  # nombre TBD + id placeholder
            ("Bye", "0", False),  # nombre Bye + id placeholder
            ("", "", False),  # ambos vacios
            (None, None, False),  # ambos None
            ("", "12345", True),  # nombre vacio pero id real (MMA: athlete.$ref)
            ("TBD", "12345", True),  # nombre TBD pero id real -> el id indica entidad legitima
            ("Roger", "0", True),  # nombre real con id placeholder -> VERDADERO (nombre gana)
            ("  BYE  ", "0", False),  # Bye con espacios
            ("tbd", "2147483647", False),  # minusculas
            ("bye", "0", False),  # minusculas
        ],
    )
    def test_competitor_is_real(self, name, cid, expected):
        assert competitor_is_real(name, cid) == expected


class TestBoutHasRealCompetitors:
    @pytest.mark.parametrize(
        "red_name,red_id,blue_name,blue_id,expected",
        [
            # Ambos reales
            ("Djokovic", "1", "Nadal", "2", True),
            # Solo uno real (ej: single player confirmado, rival TBD en bracket)
            ("Djokovic", "1", "TBD", "2147483647", True),
            ("TBD", "2147483647", "Nadal", "2", True),
            # Ninguno real (placeholder)
            ("TBD", "2147483647", "Bye", "0", False),
            ("Bye", "0", "Bye", "0", False),
            (None, None, None, None, False),
            # MMA: sin nombre inline pero con athlete.$ref (id real)
            (None, "4686725", None, "5074121", True),
            # Tenis dobles con un Bye y un TBD
            ("Bye", "0", "TBD", "2147483647", False),
        ],
    )
    def test_bout_has_real_competitors(self, red_name, red_id, blue_name, blue_id, expected):
        assert bout_has_real_competitors(red_name, red_id, blue_name, blue_id) == expected
