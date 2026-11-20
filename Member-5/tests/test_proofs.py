"""Unit tests for Member 5 Proof Substitution Engine."""
import pytest
from engine.proofs import ProofEngine


@pytest.fixture
def proofs():
    return ProofEngine()


def test_proof_rules_loaded(proofs):
    assert len(proofs.rules) >= 6
    assert "aadhaar" in proofs.rules
    assert "ration_card" in proofs.rules
    assert "land_record" in proofs.rules
    assert "_default" in proofs.rules


def test_suggest_known_documents(proofs):
    suggestions = proofs.suggest_substitutes(["aadhaar", "land_record"])
    assert len(suggestions) == 2

    aadhaar_sub = suggestions[0]
    assert aadhaar_sub["has_statutory_substitute"] is True
    assert any("panchayat" in s.lower() or "voter" in s.lower() for s in aadhaar_sub["alternatives"])

    land_sub = suggestions[1]
    assert land_sub["has_statutory_substitute"] is True
    assert any("ror" in s.lower() or "khatian" in s.lower() or "bl&lro" in s.lower() for s in land_sub["alternatives"])


def test_suggest_unknown_document_uses_default(proofs):
    suggestions = proofs.suggest_substitutes(["diploma_certificate"])
    assert len(suggestions) == 1
    assert suggestions[0]["has_statutory_substitute"] is False
    assert len(suggestions[0]["alternatives"]) > 0
    assert any("panchayat" in s.lower() for s in suggestions[0]["alternatives"])
