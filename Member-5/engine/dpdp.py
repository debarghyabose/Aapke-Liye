"""Member 5: Digital Personal Data Protection (DPDP) Act 2023 Consent & Privacy Helper.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LABELS_PATH = Path(__file__).resolve().parent.parent / "rules" / "labels.json"


class DPDPManager:
    SUPPORTED_LANGUAGES = ["en", "hi", "bn", "te", "mr", "ta"]

    def __init__(self, labels_file: Path | str | None = None):
        self.labels_path = Path(labels_file) if labels_file else LABELS_PATH
        self.labels = self.load_labels()

    def load_labels(self) -> dict[str, Any]:
        if not self.labels_path.exists():
            raise FileNotFoundError(f"Labels file not found at: {self.labels_path}")
        with open(self.labels_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_consent_text(self, language: str = "en", version: str = "v1") -> str:
        """
        Retrieves plain-language statutory consent notice for the requested language.
        """
        lang = language.lower().strip()
        consent_map = self.labels.get("consent", {})

        # Try localized key e.g. "v1_hi", "v1_bn"
        if lang != "en":
            localized_key = f"{version}_{lang}"
            if localized_key in consent_map:
                return consent_map[localized_key]

        # Default fallback to standard English consent
        return consent_map.get(version, consent_map.get("v1", ""))

    def get_document_label(self, doc_code: str) -> str:
        docs = self.labels.get("documents", {})
        return docs.get(doc_code, doc_code.replace("_", " ").title())

    def get_category_label(self, cat_code: str) -> str:
        cats = self.labels.get("categories", {})
        return cats.get(cat_code, cat_code.replace("_", " ").title())

    def get_item_label(self, cat_code: str, item_code: str) -> str:
        items = self.labels.get("items", {})
        full_key = f"{cat_code}.{item_code}"
        return items.get(full_key, item_code.replace("_", " ").title())
