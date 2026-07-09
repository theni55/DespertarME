"""Tests de notifiers: TwilioNotifier (SDK mockeado) + factory gated (D30)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.config import settings
from app.notifiers import build_notifier
from app.notifiers.base import AlertPayload
from app.notifiers.dummy import DummyNotifier
from app.notifiers.twilio import TwilioNotifier, _build_message, _build_twiml

# --- Payload de ejemplo -------------------------------------------------------


def _payload(**overrides: object) -> AlertPayload:
    defaults: dict = {
        "user_id": "u-1",
        "phone": "+34600111222",
        "event_name": "UFC 329",
        "bout_id": "b-1",
        "red_name": "Conor Test",
        "blue_name": "Max Fake",
        "weight_class": "Welterweight",
        "minutes_until_start": 15,
    }
    defaults.update(overrides)
    return AlertPayload(**defaults)


# --- Mensaje TTS ---------------------------------------------------------------


def test_build_message_includes_fighters_event_and_minutes() -> None:
    msg = _build_message(_payload())
    assert "Conor Test" in msg
    assert "Max Fake" in msg
    assert "UFC 329" in msg
    assert "15 minutos" in msg


def test_build_message_degrades_without_names() -> None:
    msg = _build_message(_payload(red_name=None, blue_name=None, minutes_until_start=0))
    assert "tu peleador" in msg
    assert "su rival" in msg
    assert "a punto de empezar" in msg


def test_build_twiml_escapes_and_repeats() -> None:
    twiml = _build_twiml("Combate <A> & B")
    assert twiml.count("<Say") == 2  # mensaje repetido 2 veces
    assert "&lt;A&gt;" in twiml
    assert "&amp;" in twiml
    assert twiml.startswith("<Response>")


# --- TwilioNotifier con SDK mockeado -------------------------------------------


async def test_twilio_notifier_creates_call_with_twiml() -> None:
    mock_client = MagicMock()
    mock_client.calls.create.return_value = MagicMock(sid="CA123")
    notifier = TwilioNotifier(from_number="+15550001111", client=mock_client)

    result = await notifier.call(_payload())

    assert result.success is True
    assert result.call_id == "CA123"
    kwargs = mock_client.calls.create.call_args.kwargs
    assert kwargs["to"] == "+34600111222"
    assert kwargs["from_"] == "+15550001111"
    assert "Conor Test" in kwargs["twiml"]


async def test_twilio_notifier_returns_failure_on_exception() -> None:
    mock_client = MagicMock()
    mock_client.calls.create.side_effect = RuntimeError("twilio down")
    notifier = TwilioNotifier(from_number="+15550001111", client=mock_client)

    result = await notifier.call(_payload())

    assert result.success is False
    assert result.call_id is None
    assert "twilio down" in (result.error or "")


# --- Factory gated por config ---------------------------------------------------


def test_build_notifier_returns_dummy_without_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "twilio_account_sid", "")
    monkeypatch.setattr(settings, "twilio_auth_token", "")
    monkeypatch.setattr(settings, "twilio_from_number", "")

    notifier = build_notifier()

    assert isinstance(notifier, DummyNotifier)


def test_build_notifier_returns_twilio_with_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "twilio_account_sid", "ACxxx")
    monkeypatch.setattr(settings, "twilio_auth_token", "token")
    monkeypatch.setattr(settings, "twilio_from_number", "+15550001111")

    notifier = build_notifier()

    assert isinstance(notifier, TwilioNotifier)


def test_build_notifier_returns_dummy_with_partial_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "twilio_account_sid", "ACxxx")
    monkeypatch.setattr(settings, "twilio_auth_token", "")
    monkeypatch.setattr(settings, "twilio_from_number", "+15550001111")

    notifier = build_notifier()

    assert isinstance(notifier, DummyNotifier)
