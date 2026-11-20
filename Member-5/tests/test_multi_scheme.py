"""Unit tests for MultiSchemeAggregator and State-Specific Proofs."""
import pytest
from engine.multi_scheme import MultiSchemeAggregator
from engine.proofs import ProofEngine


@pytest.fixture
def multi_scheme():
    return MultiSchemeAggregator()


@pytest.fixture
def proofs():
    return ProofEngine()


def test_multi_scheme_evaluation_full_destruction(multi_scheme):
    claim = {
        "claimant": {"name": "Kamala Mondal"},
        "location": {"village": "Gosaba", "is_hilly": False},
        "losses": [
            {"category": "house", "item": "fully_damaged_plain", "quantity": 1},
            {"category": "crop", "item": "rainfed", "quantity": 1.0, "damage_percent": 100}
        ],
        "is_pmfby_insured": True,
        "crop_insured_name": "paddy"
    }
    res = multi_scheme.evaluate_all(claim)
    assert res["total_schemes_count"] == 3
    codes = {s["scheme_code"] for s in res["qualifying_schemes"]}
    assert codes == {"SDRF", "PMAY_G_DISASTER", "PMFBY"}
    # SDRF: 120000 + 8500 = 128500
    # PMAY-G: 156750
    # PMFBY: 1.0 * 65000 = 65000
    # Grand total: 350250
    assert res["grand_total_estimated_inr"] == 350250


def test_state_specific_proof_resolution(proofs):
    wb_subs = proofs.suggest_substitutes(["land_record"], state="West Bengal")
    assert wb_subs[0]["state_portal"] == "Banglarbhumi (banglarbhumi.gov.in)"
    assert "BL&LRO" in wb_subs[0]["state_specific_authority"]
    assert any("banglarbhumi" in a.lower() for a in wb_subs[0]["alternatives"])

    od_subs = proofs.suggest_substitutes(["land_record"], state="Odisha")
    assert od_subs[0]["state_portal"] == "Bhulekh Odisha (bhulekh.ori.nic.in)"
    assert "Tehsildar" in od_subs[0]["state_specific_authority"]
