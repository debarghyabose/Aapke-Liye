"""Unit tests for Member 5 DPDP Act 2023 Consent & Labels Manager."""
import pytest
from engine.dpdp import DPDPManager


@pytest.fixture
def dpdp():
    return DPDPManager()


def test_consent_retrieval_across_languages(dpdp):
    for lang in DPDPManager.SUPPORTED_LANGUAGES:
        text = dpdp.get_consent_text(language=lang, version="v1")
        assert text, f"Missing consent notice for language: {lang}"
        assert len(text) > 30

        # Verify key terms in English notice matching Member 2's labels.json
        if lang == "en":
            assert "disaster relief authorities" in text.lower()
            assert "relief claim" in text.lower()


def test_labels_resolution(dpdp):
    assert "Aadhaar card" in dpdp.get_document_label("aadhaar")
    assert "House" in dpdp.get_category_label("house")
    item_label = dpdp.get_item_label("house", "fully_damaged_plain")
    assert "fully" in item_label.lower()
