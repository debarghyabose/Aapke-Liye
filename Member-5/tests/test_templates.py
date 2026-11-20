"""Unit tests for Member 5 Statutory Escalation & Reissue Templates."""
from pathlib import Path
import pytest
from engine.templates_validator import TemplateValidator


@pytest.fixture
def validator():
    return TemplateValidator()


def test_all_expected_templates_exist(validator):
    templates = {p.name: p for p in validator.list_templates()}
    expected = [
        "rti_application.en.txt",
        "grievance.en.txt",
        "followup_letter.en.txt",
        "aadhaar_reissue.en.txt",
        "ration_card_reissue.en.txt",
        "land_record_reissue.en.txt",
        "insurance_crop.en.txt",
        "insurance_home.en.txt",
        "insurance_vehicle.en.txt"
    ]
    for exp in expected:
        assert exp in templates, f"Missing template: {exp}"


def test_rti_template_has_statutory_urgency_clause(validator):
    path = validator.templates_dir / "rti_application.en.txt"
    content = path.read_text(encoding="utf-8")
    assert "Section 6(1)" in content
    assert "Section 7(1)" in content
    assert "FORTY-EIGHT (48) HOURS" in content or "48" in content
    assert "{{claim_id}}" in content
    assert "{{name}}" in content


def test_grievance_template_has_dm_act_citation(validator):
    path = validator.templates_dir / "grievance.en.txt"
    content = path.read_text(encoding="utf-8")
    assert "Disaster Management Act, 2005" in content
    assert "Section 12" in content
    assert "{{claim_id}}" in content
    assert "{{total_loss}}" in content


def test_template_mock_rendering(validator):
    path = validator.templates_dir / "followup_letter.en.txt"
    rendered = validator.render_mock(path, {
        "name": "Ramesh Mondal",
        "claim_id": "CLM-9921",
        "days_pending": "14",
        "disaster": "Cyclone Remal",
        "incident_date": "2026-11-15",
        "application_date": "2026-11-16",
        "today": "2026-11-30"
    })
    assert "Ramesh Mondal" in rendered
    assert "CLM-9921" in rendered
    assert "14 days" in rendered
