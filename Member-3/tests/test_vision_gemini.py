"""Gemini provider tests with a fake client: offline, no quota used."""
import json
from types import SimpleNamespace

import pytest
from google.genai import errors

from app import config, vision


class FakeModels:
    def __init__(self, text=None, exc=None):
        self.text, self.exc, self.last_call = text, exc, None

    def generate_content(self, **kwargs):
        self.last_call = kwargs
        if self.exc:
            raise self.exc
        return SimpleNamespace(text=self.text)


@pytest.fixture
def gemini(monkeypatch):
    def install(**kw):
        models = FakeModels(**kw)
        monkeypatch.setattr(config, "VISION_PROVIDER", "gemini")
        monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(vision, "_gemini_client", SimpleNamespace(models=models))
        return models

    return install


GOOD = json.dumps({"type": "crop", "severity": 0.6, "sdrf_category": "crop loss above 33%",
                   "real_photo": True, "description": "Paddy field under flood water."})


def test_no_gemini_key_returns_unknown(monkeypatch, photo_factory):
    monkeypatch.setattr(config, "VISION_PROVIDER", "gemini")
    assert vision.assess_damage(photo_factory()).description == "vision model not configured"


def test_parses_gemini_output(gemini, photo_factory):
    models = gemini(text=GOOD)
    result = vision.assess_damage(photo_factory())
    assert (result.type, result.severity, result.sdrf_category) == ("crop", 0.6, "crop loss above 33%")
    assert models.last_call["model"] == config.GEMINI_MODEL
    assert models.last_call["config"].response_mime_type == "application/json"


def test_blocked_or_empty_reply(gemini, photo_factory):
    gemini(text=None)
    assert vision.assess_damage(photo_factory()).type == "unknown"


def test_rate_limit_is_handled(gemini, photo_factory):
    gemini(exc=errors.ClientError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}}))
    assert vision.assess_damage(photo_factory()).description == "vision daily limit reached, retry later"


def test_busy_model_falls_back_to_next(monkeypatch, photo_factory):
    calls = []

    class Busy:
        def generate_content(self, **kw):
            calls.append(kw["model"])
            if len(calls) == 1:
                raise errors.ServerError(503, {"error": {"message": "high demand", "status": "UNAVAILABLE"}})
            return SimpleNamespace(text=GOOD)

    monkeypatch.setattr(config, "VISION_PROVIDER", "gemini")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(config, "GEMINI_MODELS", ["model-a", "model-b"])
    monkeypatch.setattr(vision, "_gemini_client", SimpleNamespace(models=Busy()))
    result = vision.assess_damage(photo_factory())
    assert calls == ["model-a", "model-b"]
    assert result.type == "crop"


def test_all_models_busy_is_retryable(monkeypatch, gemini, photo_factory):
    monkeypatch.setattr(config, "GEMINI_MODELS", ["model-a", "model-b"])
    gemini(exc=errors.ServerError(503, {"error": {"message": "high demand", "status": "UNAVAILABLE"}}))
    assert vision.assess_damage(photo_factory()).description == "vision service error"


def test_unknown_provider(monkeypatch, photo_factory):
    monkeypatch.setattr(config, "VISION_PROVIDER", "nope")
    assert "unknown VISION_PROVIDER" in vision.assess_damage(photo_factory()).description
