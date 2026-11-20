"""Unit tests for MultiSchemeAggregator, State-Specific Proofs, and Mesh Policy."""
import json
from pathlib import Path
import pytest
from engine.multi_scheme import MultiSchemeAggregator
from engine.proofs import ProofEngine
from engine.dpdp import DPDPManager


@pytest.fixture
def multi_scheme():
    return MultiSchemeAggregator()


@pytest.fixture
def proofs():
    return ProofEngine()


@pytest.fixture
def dpdp():
    return DPDPManager()


def test_two_block_entitlement_structure(multi_scheme):
    """Verify I1: Relief owed (SDRF) is strictly separated from conditional schemes."""
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

    # 1. Relief Owed block (SDRF only)
    owed = res["relief_owed"]
    assert owed["scheme_code"] == "SDRF"
    assert owed["estimated_amount"] == 128500  # 120,000 + 8,500
    assert "conditions" in owed

    # 2. May Also Qualify block (PMAY-G & PMFBY)
    qualify = res["may_also_qualify"]
    assert len(qualify) == 2
    codes = {s["scheme_code"] for s in qualify}
    assert codes == {"PMAY_G_DISASTER", "PMFBY"}

    for s in qualify:
        assert "conditions" in s
        assert len(s["conditions"]) >= 2  # conditions must be clearly stated
        assert s["estimated_amount"] > 0


def test_pmfby_zero_damage_yields_zero(multi_scheme):
    """C3: PMFBY with 0% damage must evaluate to 0 payout, NOT full sum insured."""
    claim = {
        "claimant": {"name": "Ram Das"},
        "losses": [
            {"category": "crop", "item": "rainfed", "quantity": 1.0, "damage_percent": 0}
        ],
        "is_pmfby_insured": True,
        "crop_insured_name": "paddy"
    }
    res = multi_scheme.evaluate_all(claim)
    pmfby_schemes = [s for s in res["may_also_qualify"] if s["scheme_code"] == "PMFBY"]
    assert len(pmfby_schemes) == 0  # 0% damage -> no claim payable


def test_pmfby_indemnity_level_applied(multi_scheme):
    """C5: PMFBY calculation must apply default indemnity level (0.80)."""
    claim = {
        "claimant": {"name": "Ram Das"},
        "losses": [
            {"category": "crop", "item": "rainfed", "quantity": 1.0, "damage_percent": 100}
        ],
        "is_pmfby_insured": True,
        "crop_insured_name": "paddy"
    }
    res = multi_scheme.evaluate_all(claim)
    pmfby = next(s for s in res["may_also_qualify"] if s["scheme_code"] == "PMFBY")
    # Paddy sum insured = 65,000; indemnity = 0.80; 1.0 ha * 100% = 52,000
    assert pmfby["estimated_amount"] == 52000
    assert pmfby["breakdown"][0]["indemnity_level"] == 0.80


def test_pmay_amounts_loaded_from_json(multi_scheme):
    """C6: PMAY-G amounts must be read from json schema, not typed in Python."""
    claim = {
        "location": {"is_hilly": False},
        "losses": [{"category": "house", "item": "fully_damaged_plain", "quantity": 1}]
    }
    res = multi_scheme.evaluate_all(claim)
    pmay = next(s for s in res["may_also_qualify"] if s["scheme_code"] == "PMAY_G_DISASTER")
    # Plain areas package = 156,750
    assert pmay["estimated_amount"] == 156750
    components = {b["component"]: b["amount"] for b in pmay["breakdown"]}
    assert components["Housing Construction Unit Grant"] == 120000
    assert components["90 Days MGNREGA Unskilled Labor Allowance"] == 24750
    assert components["Swachh Bharat Gramin Toilet Grant"] == 12000


def test_state_specific_proof_resolution(proofs):
    wb_subs = proofs.suggest_substitutes(["land_record"], state="West Bengal")
    assert wb_subs[0]["state_portal"] == "Banglarbhumi (banglarbhumi.gov.in)"
    assert "BL&LRO" in wb_subs[0]["state_specific_authority"]
    assert any("banglarbhumi" in a.lower() for a in wb_subs[0]["alternatives"])

    od_subs = proofs.suggest_substitutes(["land_record"], state="Odisha")
    assert od_subs[0]["state_portal"] == "Bhulekh Odisha (bhulekh.ori.nic.in)"
    assert "Tehsildar" in od_subs[0]["state_specific_authority"]


def test_mesh_policy_and_carrier_consent(dpdp):
    """Verify mesh_policy.json and carrier consent strings across 6 languages."""
    policy_path = Path(__file__).resolve().parent.parent / "rules" / "mesh_policy.json"
    assert policy_path.exists()
    policy = json.loads(policy_path.read_text(encoding="utf-8"))

    # Check key operational limits
    assert policy["storage"]["max_payload_bytes"] == 1572864  # 1.5 MB
    assert policy["storage"]["max_relay_storage_mb"] == 30
    assert policy["battery"]["battery_floor_percent"] == 25
    assert policy["storage"]["ttl_seconds"] == 604800  # 7 days

    # Check carrier consent across all 6 languages
    for lang in DPDPManager.SUPPORTED_LANGUAGES:
        text = dpdp.get_consent_text(language=lang, version="carrier_v1")
        assert text, f"Missing carrier consent for language {lang}"
        assert len(text) > 20
