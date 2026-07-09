"""Validadores de datos de usuario (MVP launch, D34).

El teléfono es obligatorio y en formato E.164 (`+34600111222`): sin él Twilio
no puede llamar. Se normaliza quitando espacios/guiones antes de validar.
"""

from __future__ import annotations

import re

# E.164: `+` seguido de 8 a 15 dígitos, sin cero inicial.
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_phone_e164(raw: str) -> str:
    """Normaliza y valida un teléfono E.164. Lanza ValueError si no es válido."""
    cleaned = re.sub(r"[\s\-().]", "", raw or "")
    if not _E164_RE.match(cleaned):
        raise ValueError("Teléfono inválido: usa formato internacional E.164, p. ej. +34600111222")
    return cleaned
