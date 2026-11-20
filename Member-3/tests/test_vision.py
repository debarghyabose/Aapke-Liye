"""Vision tests use a fake client, so they run offline and cost nothing."""
from types import SimpleNamespace

import pytest

from app import config, vision
from app.schemas import Checks
from app.scoring import score


class FakeMessages:
    def __init__(self, parsed=None, stop_reason="end_turn", exc=None):
        self.parsed, self.stop_reason, self.exc = parsed, stop_reason, exc
        self.last_call = None

    def parse(self, **kwargs):
        self.last_call = kwargs
        if self.exc:
            raise self.exc
        return SimpleNamespace(parsed_output=self.parsed, stop_reason=self.stop_reason)


@pytest.fixture
def fake(monkeypatch):
    def install(**kw):
        messages = FakeMessages(**kw)
        monkeypatch.setattr(config, "VISION_PROVIDER", "claude")
        monkeypatch.setattr(config, "VISION_API_KEY", "test-key")
        monkeypatch.setattr(vision, "_client", SimpleNamespace(messages=messages))
        return messages

    return install


def output(**kw):
    base = dict(type="house", severity=0.8, sdrf_category="kutcha house fully damaged",
                real_photo=True, description="Mud house collapsed after flooding.")
    base.update(kw)
    return vision._VisionOutput(**base)


def test_no_key_returns_unknown(photo_factory):
    assert vision.assess_damage(photo_factory()).type == "unknown"


def test_parses_model_output(fake, photo_factory):
    msgs = fake(parsed=output())
    result = vision.assess_damage(photo_factory())
    assert result.type == "house"
    assert result.severity == 0.8
    assert result.real_photo is True
    sent = msgs.last_call["messages"][0]["content"][0]
    assert sent["type"] == "image" and sent["source"]["media_type"] == "image/jpeg"


def test_severity_is_clamped(fake, photo_factory):
    fake(parsed=output(severity=1.7))
    assert vision.assess_damage(photo_factory()).severity == 1.0


def test_refusal_goes_to_review(fake, photo_factory):
    fake(parsed=None, stop_reason="refusal")
    assert vision.assess_damage(photo_factory()).type == "unknown"


def test_api_error_does_not_crash(fake, photo_factory):
    import anthropic
    import httpx2

    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    fake(exc=anthropic.APIConnectionError(request=req))
    assert vision.assess_damage(photo_factory()).description == "vision service unreachable"


def test_bad_image_bytes(fake):
    fake(parsed=output())
    assert vision.assess_damage(b"not an image").description == "could not read image"


def test_fake_photo_lowers_score():
    good = score("a", Checks(gps_in_zone=True, timestamp_valid=True, damage=vision.DamageResult(
        type="house", severity=0.8, real_photo=True)))
    fake_photo = score("b", Checks(gps_in_zone=True, timestamp_valid=True, damage=vision.DamageResult(
        type="house", severity=0.8, real_photo=False)))
    assert good.status == "auto_verified"
    assert fake_photo.status != "auto_verified"
    assert "not_genuine_photo" in fake_photo.flags
