"""
Real Firebase Firestore Database Service for Aapke Liye
Uses project: trusty-obelisk-515402-p3
"""
import logging
import os
import subprocess
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.cloud import firestore
from google.oauth2.credentials import Credentials

from . import config

log = logging.getLogger(__name__)

def _get_credentials():
    """Returns credentials for Firestore: ADC or gcloud access token."""
    # 1. Standard Google credentials
    try:
        from google.auth import default
        creds, _ = default()
        if creds:
            return creds
    except Exception:
        pass

    # 2. Local fallback via gcloud CLI
    try:
        gcloud_cmd = "gcloud.cmd" if os.name == "nt" else "gcloud"
        token = subprocess.check_output([gcloud_cmd, "auth", "print-access-token"], text=True, timeout=5).strip()
        if token:
            return Credentials(token)
    except Exception as e:
        log.warning("Could not obtain gcloud access token: %s", e)

    return None


class FirestoreDatabase:
    def __init__(self):
        self._client: Optional[firestore.Client] = None
        self._lock = threading.Lock()
        self._memory_claims: Dict[str, Dict[str, Any]] = {}
        self._memory_households: Dict[str, Dict[str, Any]] = {}
        self._memory_envelopes: Dict[str, Dict[str, Any]] = {}
        self._memory_receipts: Dict[str, Dict[str, Any]] = {}
        self._memory_audit: List[Dict[str, Any]] = []

    def get_client(self) -> Optional[firestore.Client]:
        if self._client is not None:
            return self._client
        with self._lock:
            if self._client is None:
                try:
                    creds = _get_credentials()
                    self._client = firestore.Client(project=config.PROJECT_ID, credentials=creds)
                    log.info("Connected to Firestore on project %s", config.PROJECT_ID)
                except Exception as e:
                    log.error("Failed to connect to Firestore: %s. Using local fallback cache.", e)
                    self._client = None
        return self._client

    # ---------------- Claims ----------------
    def save_claim(self, claim_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        client = self.get_client()
        if client:
            try:
                doc_ref = client.collection("claims").document(claim_id)
                doc_ref.set(data)
            except Exception as e:
                log.error("Firestore save_claim failed: %s", e)
        self._memory_claims[claim_id] = data
        return data

    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        client = self.get_client()
        if client:
            try:
                doc = client.collection("claims").document(claim_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                log.error("Firestore get_claim failed: %s", e)
        return self._memory_claims.get(claim_id)

    def update_claim(self, claim_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        claim = self.get_claim(claim_id)
        if not claim:
            return None
        claim.update(updates)
        return self.save_claim(claim_id, claim)

    def list_claims(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        client = self.get_client()
        if client:
            try:
                query = client.collection("claims")
                if status:
                    query = query.where("status", "==", status)
                docs = query.limit(limit).stream()
                results = [doc.to_dict() for doc in docs]
                if results:
                    return results
            except Exception as e:
                log.error("Firestore list_claims failed: %s", e)
        
        claims = list(self._memory_claims.values())
        if status:
            claims = [c for c in claims if c.get("status") == status]
        return claims[:limit]

    # ---------------- Pre-disaster Household Vault ----------------
    def save_household(self, household_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        client = self.get_client()
        if client:
            try:
                client.collection("households").document(household_id).set(data)
            except Exception as e:
                log.error("Firestore save_household failed: %s", e)
        self._memory_households[household_id] = data
        return data

    def get_household(self, household_id: str) -> Optional[Dict[str, Any]]:
        client = self.get_client()
        if client:
            try:
                doc = client.collection("households").document(household_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                log.error("Firestore get_household failed: %s", e)
        return self._memory_households.get(household_id)

    def update_household(self, household_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        hh = self.get_household(household_id)
        if not hh:
            return None
        hh.update(updates)
        return self.save_household(household_id, hh)

    # ---------------- Mesh Envelopes & Receipts ----------------
    def save_mesh_envelope(self, claim_id: str, envelope: Dict[str, Any]):
        client = self.get_client()
        if client:
            try:
                client.collection("mesh_envelopes").document(claim_id).set(envelope)
            except Exception as e:
                log.error("Firestore save_mesh_envelope failed: %s", e)
        self._memory_envelopes[claim_id] = envelope

    def get_mesh_envelope(self, claim_id: str) -> Optional[Dict[str, Any]]:
        client = self.get_client()
        if client:
            try:
                doc = client.collection("mesh_envelopes").document(claim_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                log.error("Firestore get_mesh_envelope failed: %s", e)
        return self._memory_envelopes.get(claim_id)

    def save_mesh_receipt(self, claim_id: str, receipt: Dict[str, Any]):
        client = self.get_client()
        if client:
            try:
                client.collection("mesh_receipts").document(claim_id).set(receipt)
            except Exception as e:
                log.error("Firestore save_mesh_receipt failed: %s", e)
        self._memory_receipts[claim_id] = receipt

    def get_mesh_receipt(self, claim_id: str) -> Optional[Dict[str, Any]]:
        client = self.get_client()
        if client:
            try:
                doc = client.collection("mesh_receipts").document(claim_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                log.error("Firestore get_mesh_receipt failed: %s", e)
        return self._memory_receipts.get(claim_id)

    # ---------------- Fraud Detection & Cross-Claim Duplicates ----------------
    def find_duplicate_photo(self, sha256_hash: str, current_claim_id: str) -> Optional[str]:
        """Finds if a photo with this sha256 was used in another claim."""
        all_claims = self.list_claims(limit=500)
        for claim in all_claims:
            if claim.get("id") == current_claim_id:
                continue
            for p in claim.get("photos", []):
                if p.get("sha256") == sha256_hash:
                    return claim.get("id")
        return None

    # ---------------- Audit Trail ----------------
    def log_audit(self, claim_id: Optional[str], event: str, actor: str = "system", **extra):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "claim_id": claim_id,
            "event": event,
            "actor": actor,
            "extra": extra,
        }
        client = self.get_client()
        if client:
            try:
                client.collection("audit_logs").add(entry)
            except Exception as e:
                log.error("Firestore log_audit failed: %s", e)
        self._memory_audit.append(entry)


db = FirestoreDatabase()
