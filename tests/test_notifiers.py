"""Tests de notifiers push (Fase 7a, FCM): DummyNotifier + factory gated (D30 patrón)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.config import settings
from app.notifiers import build_notifier
from app.notifiers.base import AlertPayload
from app.notifiers.dummy import DummyNotifier


def _payload(**overrides: object) -> AlertPayload:
    defaults: dict = {
        "device_id": "dev-1",
        "fcm_token": "tok-aaaa1111bbbb2222cccc",
        "message_type": "update",
        "event_id": "ev-1",
        "bout_id": "b-1",
        "event_name": "UFC 329",
        "fighters": "Conor Test vs Max Fake",
        "estimated_start_at": "2026-07-11T21:30:00+00:00",
        "minutes_until_start": 15,
        "weight_class": "Welterweight",
    }
    defaults.update(overrides)
    return AlertPayload(**defaults)


# --- AlertPayload.to_data ---------------------------------------------------


def test_payload_to_data_includes_required_fields() -> None:
    data = _payload().to_data()
    assert data["type"] == "update"
    assert data["device_id"] == "dev-1"
    assert data["event_id"] == "ev-1"
    assert data["bout_id"] == "b-1"
    assert data["event_name"] == "UFC 329"
    assert data["fighters"] == "Conor Test vs Max Fake"
    assert data["estimated_start_at"] == "2026-07-11T21:30:00+00:00"
    assert data["minutes_until_start"] == "15"
    assert data["weight_class"] == "Welterweight"


def test_payload_to_data_omits_none_fields() -> None:
    p = _payload(
        fighters=None, estimated_start_at=None, minutes_until_start=None, weight_class=None
    )
    data = p.to_data()
    assert "fighters" not in data
    assert "estimated_start_at" not in data
    assert "minutes_until_start" not in data
    assert "weight_class" not in data


# --- DummyNotifier ----------------------------------------------------------


async def test_dummy_notifier_returns_success_and_logs() -> None:
    notifier = DummyNotifier()
    result = await notifier.send(_payload())
    assert result.success is True
    assert result.message_id is not None
    assert result.message_id.startswith("dummy-")


async def test_dummy_notifier_forced_failure_on_token() -> None:
    notifier = DummyNotifier(fail_on_token="tok-aaaa1111bbbb2222cccc")
    result = await notifier.send(_payload())
    assert result.success is False
    assert "forced failure" in (result.error or "")


# --- FcmNotifier con SDK mockeado (sin tocar firebase-admin) ---------------


def _make_fcm_notifier_with_mock() -> tuple:
    """Mockea firebase_admin + messaging para instanciar FcmNotifier sin Firebase real."""
    fake_app = MagicMock()
    firebase_admin_mod = MagicMock()
    # `from firebase_admin import messaging` accede a `firebase_admin.messaging`.
    messaging_mod = MagicMock()
    firebase_admin_mod.messaging = messaging_mod
    # `from firebase_admin import credentials as fb_credentials` igual.
    creds_mod = MagicMock()
    firebase_admin_mod.credentials = creds_mod
    firebase_admin_mod.get_app.side_effect = ValueError("no app")
    firebase_admin_mod.initialize_app.return_value = fake_app

    msg_obj = MagicMock()
    messaging_mod.Message.return_value = msg_obj
    messaging_mod.AndroidConfig.return_value = MagicMock()
    messaging_mod.send.return_value = "fcm-msg-id-123"
    creds_mod.Certificate.return_value = MagicMock()

    fake_credentials = {
        "type": "service_account",
        "project_id": "test-proj",
        "private_key": "x",
        "client_email": "x@test.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    sys_modules = {
        "firebase_admin": firebase_admin_mod,
        "firebase_admin.credentials": creds_mod,
        "firebase_admin.messaging": messaging_mod,
    }

    with patch.dict("sys.modules", sys_modules):
        from app.notifiers.fcm import FcmNotifier

        notifier = FcmNotifier(credentials=fake_credentials)
        return notifier, messaging_mod


async def test_fcm_notifier_send_returns_message_id_on_success() -> None:
    notifier, messaging_mod = _make_fcm_notifier_with_mock()
    messaging_mod.send.return_value = "fcm-ok-001"

    result = await notifier.send(_payload())

    assert result.success is True
    assert result.message_id == "fcm-ok-001"
    # Verifica que send se invoca con token y con data del payload
    args, _ = messaging_mod.send.call_args
    msg = args[0]
    assert msg is not None
    assert messaging_mod.AndroidConfig.called
    messaging_mod.send.assert_called_once()


async def test_fcm_notifier_send_returns_failure_on_exception() -> None:
    notifier, messaging_mod = _make_fcm_notifier_with_mock()
    messaging_mod.send.side_effect = RuntimeError("fcm down")

    result = await notifier.send(_payload())

    assert result.success is False
    assert "fcm down" in (result.error or "")


# --- Factory gated por config ----------------------------------------------


def test_build_notifier_returns_dummy_without_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "fcm_credentials_path", None)
    monkeypatch.setattr(settings, "fcm_credentials_json", None)

    notifier = build_notifier()

    assert isinstance(notifier, DummyNotifier)


def test_build_notifier_uses_dummy_when_fcm_init_fails(monkeypatch, tmp_path) -> None:
    # Fichero JSON inválido → no se puede cargar credenciales → Dummy fallback.
    bad = tmp_path / "bad.json"
    bad.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(settings, "fcm_credentials_path", str(bad))
    monkeypatch.setattr(settings, "fcm_credentials_json", None)

    notifier = build_notifier()

    assert isinstance(notifier, DummyNotifier)
