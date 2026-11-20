"""Member 5: Statutory Escalation & Reissue Template Validator.
Verifies Jinja2/string placeholders and legal citations across all templates.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class TemplateValidator:
    PLACEHOLDER_REGEX = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")

    def __init__(self, templates_dir: Path | str | None = None):
        self.templates_dir = Path(templates_dir) if templates_dir else TEMPLATES_DIR

    def list_templates(self) -> list[Path]:
        return list(self.templates_dir.glob("*.txt"))

    def extract_placeholders(self, template_path: Path) -> set[str]:
        content = template_path.read_text(encoding="utf-8")
        return set(self.PLACEHOLDER_REGEX.findall(content))

    def render_mock(self, template_path: Path, data: dict[str, Any]) -> str:
        """Render template replacing {{key}} with values or placeholder defaults."""
        content = template_path.read_text(encoding="utf-8")
        placeholders = self.extract_placeholders(template_path)
        for p in placeholders:
            val = str(data.get(p, f"[{p.upper()}]"))
            content = content.replace(f"{{{{{p}}}}}", val)
        return content
