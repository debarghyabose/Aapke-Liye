"""Member 5: Inter-Member System Connector & Synchronization Diagnostic.
Performs deep content comparison between Member 5 deliverables and other members' folders:
- Compares Member 5 templates with Member 1 templates (detects unmodified placeholders)
- Compares Member 5 rules with Member 2 rules (detects unmerged sample rules)
- Inspects Member 3 verification modules and Member 4 frontend implementation status.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


class SystemConnector:
    def __init__(self, root: Path | None = None):
        self.root = root or WORKSPACE_ROOT
        self.m1_dir = self.root / "Member-1"
        self.m2_dir = self.root / "Member-2"
        self.m3_dir = self.root / "Member-3"
        self.m4_dir = self.root / "Member-4"
        self.m5_dir = self.root / "Member-5"

    def check_connection_status(self) -> dict[str, Any]:
        """
        Runs comprehensive diagnostic on connections and content synchronization.
        """
        status: dict[str, Any] = {
            "member_1": {"connected": False, "sync_status": "Disconnected", "details": []},
            "member_2": {"connected": False, "sync_status": "Disconnected", "details": []},
            "member_3": {"connected": False, "sync_status": "Disconnected", "details": []},
            "member_4": {"connected": False, "sync_status": "Disconnected", "details": []},
        }

        # ----------------------------------------------------
        # 1. Member 1: Compare template contents
        # ----------------------------------------------------
        m1_templates = self.m1_dir / "app" / "templates"
        m5_templates = self.m5_dir / "templates"

        if not m1_templates.exists():
            status["member_1"]["sync_status"] = "Missing"
            status["member_1"]["details"].append("Member-1/app/templates directory not found")
        else:
            m5_files = sorted(m5_templates.glob("*.txt"))
            synced_files = []
            out_of_sync_files = []

            for f5 in m5_files:
                f1 = m1_templates / f5.name
                if not f1.exists():
                    out_of_sync_files.append((f5.name, "File missing in Member-1"))
                    continue

                content_5 = f5.read_text(encoding="utf-8").strip()
                content_1 = f1.read_text(encoding="utf-8").strip()

                if "PLACEHOLDER TEMPLATE" in content_1:
                    out_of_sync_files.append((f5.name, "Member 1 still using placeholder"))
                elif content_5 == content_1:
                    synced_files.append(f5.name)
                else:
                    out_of_sync_files.append((f5.name, "Content mismatch"))

            total_m5 = len(m5_files)
            synced_count = len(synced_files)

            if synced_count == total_m5 and total_m5 > 0:
                status["member_1"]["connected"] = True
                status["member_1"]["sync_status"] = "In sync"
                status["member_1"]["details"].append(f"All {total_m5} statutory templates adopted by Member 1")
            else:
                status["member_1"]["connected"] = False
                status["member_1"]["sync_status"] = "Out of sync"
                status["member_1"]["details"].append(
                    f"Out of sync ({synced_count}/{total_m5} adopted): Member 1 still contains placeholder templates pending adoption of Member 5 text"
                )

        # ----------------------------------------------------
        # 2. Member 2: Compare rules JSON contents
        # ----------------------------------------------------
        m2_rules = self.m2_dir / "backend" / "rules"
        m5_rules = self.m5_dir / "rules"

        if not m2_rules.exists():
            status["member_2"]["sync_status"] = "Missing"
            status["member_2"]["details"].append("Member-2/backend/rules directory not found")
        else:
            rule_files = ["sdrf_rules.json", "proof_substitution.json", "labels.json"]
            mismatches = []

            for rname in rule_files:
                f2 = m2_rules / rname
                f5 = m5_rules / rname
                if not f2.exists():
                    mismatches.append(f"{rname} missing in Member 2")
                    continue
                try:
                    data2 = json.loads(f2.read_text(encoding="utf-8"))
                    data5 = json.loads(f5.read_text(encoding="utf-8"))
                    # Full content comparison: a changed rate or substitute is a mismatch
                    # even when the version string is the same.
                    if data2 != data5:
                        if rname == "sdrf_rules.json" and data2.get("version") != data5.get("version"):
                            mismatches.append(
                                f"sdrf_rules.json version mismatch: Member 2 has '{data2.get('version')}', Member 5 has '{data5.get('version')}'"
                            )
                        else:
                            mismatches.append(f"{rname} content differs from Member 5's copy")
                except Exception as e:
                    mismatches.append(f"Error parsing {rname}: {e}")

            if not mismatches:
                status["member_2"]["connected"] = True
                status["member_2"]["sync_status"] = "In sync"
                status["member_2"]["details"].append("Member 2 backend is running verified Member 5 rules")
            else:
                status["member_2"]["connected"] = False
                status["member_2"]["sync_status"] = "Out of sync"
                status["member_2"]["details"].append(
                    f"Out of sync: Member 2 is still using initial sample rules ({'; '.join(mismatches)}). Pending Member 2 adoption."
                )

        # ----------------------------------------------------
        # 3. Member 3: Verification module telemetry check
        # ----------------------------------------------------
        m3_app = self.m3_dir / "app"
        has_vision = m3_app.exists() and (m3_app / "vision.py").exists()
        has_dups = m3_app.exists() and (m3_app / "duplicates.py").exists()

        if has_vision and has_dups:
            status["member_3"]["connected"] = True
            status["member_3"]["sync_status"] = "Telemetry Ready"
            status["member_3"]["details"].append(
                "Damage vision & duplicate detector algorithms ready for dashboard ingestion"
            )
        else:
            status["member_3"]["connected"] = False
            status["member_3"]["sync_status"] = "Incomplete"
            status["member_3"]["details"].append("Member 3 vision or duplicate detector not fully ready")

        # ----------------------------------------------------
        # 4. Member 4: Frontend implementation check
        # ----------------------------------------------------
        # Member 4 only owns screens; check if any code/html exists in Member-4
        skip = {"node_modules", "dist", ".vite"}
        m4_files = [p for p in self.m4_dir.rglob("*")
                    if p.is_file() and p.name != "README.md" and not skip & set(p.parts)]
        if not m4_files:
            status["member_4"]["connected"] = False
            status["member_4"]["sync_status"] = "Pending Implementation"
            status["member_4"]["details"].append(
                "Pending implementation: Member 4 has not yet built frontend screens (only README.md present)"
            )
        else:
            status["member_4"]["connected"] = True
            status["member_4"]["sync_status"] = "In progress"
            status["member_4"]["details"].append(f"{len(m4_files)} frontend files found")

        return status


if __name__ == "__main__":
    conn = SystemConnector()
    print(json.dumps(conn.check_connection_status(), indent=2))
