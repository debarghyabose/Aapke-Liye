"""Unit tests for Member 5 SDRF Entitlement Calculation Engine."""
import pytest
from engine.entitlement import EntitlementEngine, inr


@pytest.fixture
def engine():
    return EntitlementEngine()


def test_inr_formatting():
    assert inr(0) == "0"
    assert inr(1000) == "1,000"
    assert inr(120000) == "1,20,000"
    assert inr(143200) == "1,43,200"
    assert inr(10000000) == "1,00,00,000"


def test_house_full_damage_calculation(engine):
    losses = [{"category": "house", "item": "fully_damaged_plain", "quantity": 1}]
    result = engine.calculate(losses)
    assert result["total"] == 120000
    assert result["total_inr_formatted"] == "1,20,000"
    assert len(result["lines"]) == 1
    assert result["lines"][0]["amount"] == 120000
    assert result["lines"][0]["eligible"] is True


def test_crop_damage_threshold_and_capping(engine):
    # Below 33% threshold -> not eligible (0)
    ineligible = [{"category": "crop", "item": "rainfed", "quantity": 1.5, "damage_percent": 25}]
    res1 = engine.calculate(ineligible)
    assert res1["total"] == 0
    assert res1["lines"][0]["eligible"] is False
    assert "below statutory threshold" in res1["lines"][0]["note"]

    # At or above 33% threshold -> eligible, capped at 2.0 ha
    eligible_capped = [{"category": "crop", "item": "rainfed", "quantity": 3.0, "damage_percent": 50}]
    res2 = engine.calculate(eligible_capped)
    # 2.0 ha * 8500 = 17,000
    assert res2["total"] == 17000
    assert "capped at 2" in res2["lines"][0]["note"].lower()


def test_livestock_milch_and_poultry_caps(engine):
    losses = [
        {"category": "livestock", "item": "milch_large", "quantity": 2},
        {"category": "livestock", "item": "poultry", "quantity": 150}
    ]
    res = engine.calculate(losses)
    # milch_large: 2 * 37,500 = 75,000
    # poultry: 150 * 100 = 15,000 -> capped at 10,000
    assert res["lines"][0]["amount"] == 75000
    assert res["lines"][1]["amount"] == 10000
    assert "statutory maximum limit" in res["lines"][1]["note"].lower()
    assert res["total"] == 85000


def test_household_emergency_sustenance(engine):
    losses = [
        {"category": "household", "item": "clothing", "quantity": 1},
        {"category": "household", "item": "utensils", "quantity": 1}
    ]
    res = engine.calculate(losses)
    assert res["total"] == 5000


def test_ex_gratia_death_and_disability(engine):
    losses = [
        {"category": "ex_gratia", "item": "death", "quantity": 1},
        {"category": "ex_gratia", "item": "disability_above_60", "quantity": 1}
    ]
    res = engine.calculate(losses)
    # 400000 + 250000 = 650000
    assert res["total"] == 650000


def test_unmatched_loss_handling(engine):
    losses = [
        {"category": "spacecraft", "item": "rocket", "quantity": 1},
        {"category": "house", "item": "skyscraper", "quantity": 1}
    ]
    res = engine.calculate(losses)
    assert res["total"] == 0
    assert len(res["unmatched"]) == 2
    assert "Unknown category 'spacecraft'" in res["unmatched"][0]["reason"]
    assert "Unknown item 'skyscraper'" in res["unmatched"][1]["reason"]
