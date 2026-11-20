"""Integration and system connection tests for Member 5."""
from engine.connector import SystemConnector


def test_system_connections_diagnostic():
    connector = SystemConnector()
    status = connector.check_connection_status()

    # Verify all members are evaluated in diagnostic
    assert "member_1" in status
    assert "member_2" in status
    assert "member_3" in status
    assert "member_4" in status

    # Verify deep content synchronization flags:
    # Member 1 still has placeholder templates -> must be flagged "Out of sync"
    assert status["member_1"]["sync_status"] == "Out of sync"
    assert "placeholder" in status["member_1"]["details"][0].lower()

    # Member 2 is still using sample rates -> must be flagged "Out of sync"
    assert status["member_2"]["sync_status"] == "Out of sync"
    assert "sample" in status["member_2"]["details"][0].lower() or "version" in status["member_2"]["details"][0].lower()

    # Member 3 algorithms ready for dashboard telemetry
    assert status["member_3"]["sync_status"] == "Telemetry Ready"

    # Member 4 has not yet built frontend screens -> must be flagged "Pending Implementation"
    assert status["member_4"]["sync_status"] == "Pending Implementation"


def test_member2_rules_compatibility():
    """Verify Member 5's sdrf_rules.json conforms to Member 2's validation schema."""
    import json
    from pathlib import Path
    m5_rules = json.loads(
        (Path(__file__).resolve().parent.parent / "rules" / "sdrf_rules.json").read_text(encoding="utf-8")
    )
    assert "version" in m5_rules
    assert "categories" in m5_rules
    for cat_name, cat in m5_rules["categories"].items():
        assert "unit" in cat
        assert "items" in cat
        for item, rate in cat["items"].items():
            assert isinstance(rate, (int, float)) and rate >= 0
