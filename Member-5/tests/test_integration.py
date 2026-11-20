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

    # Members 1 and 2 now run Member 5's exact files
    assert status["member_1"]["sync_status"] == "In sync"
    assert status["member_2"]["sync_status"] == "In sync"

    # Member 3 algorithms ready for dashboard telemetry
    assert status["member_3"]["sync_status"] == "Telemetry Ready"

    # Member 4 has built the frontend (node_modules and build output are not counted)
    assert status["member_4"]["sync_status"] == "In progress"


def test_connector_flags_changed_rates(tmp_path):
    """Same version string but a different rate must still be reported as out of sync."""
    import json
    import shutil
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    for d in ["Member-1/app/templates", "Member-3/app", "Member-4", "Member-5/templates", "Member-5/rules"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / "Member-5/rules", tmp_path / "Member-5/rules", dirs_exist_ok=True)
    shutil.copytree(root / "Member-2/backend/rules", tmp_path / "Member-2/backend/rules")
    rules = tmp_path / "Member-2/backend/rules/sdrf_rules.json"
    data = json.loads(rules.read_text(encoding="utf-8"))
    data["categories"]["house"]["items"]["fully_damaged_plain"] = 1
    rules.write_text(json.dumps(data), encoding="utf-8")
    status = SystemConnector(root=tmp_path).check_connection_status()
    assert status["member_2"]["sync_status"] == "Out of sync"
    assert "content differs" in status["member_2"]["details"][0]


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
