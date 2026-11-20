from app.gaps import clean_phone, missing_fields
from app.schemas import Claim, Loss


def full_claim() -> Claim:
    c = Claim(session_id="s1", language="hi")
    c.claimant.name = "Ramesh Kumar"
    c.claimant.phone = "9876543210"
    c.location.village = "Satapada"
    c.location.district = "Puri"
    c.location.state = "Odisha"
    c.disaster_type = "cyclone"
    c.incident_date = "2026-11-12"
    c.losses = [Loss(type="house", house_kind="kutcha", damage_level="destroyed", amount_inr=200000)]
    return c


def test_complete_claim_has_nothing_missing():
    assert missing_fields(full_claim()) == []


def test_empty_claim_order():
    m = missing_fields(Claim(session_id="s"))
    assert m[0] == "claimant.name"
    assert m == ["claimant.name", "disaster_type", "losses", "location.village", "location.district",
                 "location.state", "incident_date", "claimant.phone"]


def test_crop_needs_area_and_crop():
    c = full_claim()
    c.losses = [Loss(type="crop", amount_inr=50000)]
    assert missing_fields(c) == ["losses[0].crop_name", "losses[0].area_acres"]


def test_livestock_needs_count():
    c = full_claim()
    c.losses.append(Loss(type="livestock", animal="cow", amount_inr=60000))
    assert missing_fields(c) == ["losses[1].count"]


def test_bad_phone_and_future_date():
    c = full_claim()
    c.claimant.phone = "12345"
    c.incident_date = "2999-01-01"
    assert set(missing_fields(c)) == {"claimant.phone", "incident_date"}


def test_clean_phone():
    assert clean_phone("+91 98765 43210") == "9876543210"
    assert clean_phone("09876543210") == "9876543210"
    assert clean_phone("1234567890") is None
