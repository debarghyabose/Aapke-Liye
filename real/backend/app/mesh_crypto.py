"""
Cryptographic Mesh Relay Engine for Aapke Liye
Implements RSA-OAEP-256 + AES-256-GCM envelope opening and Ed25519 receipt signing.
"""
import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import config

log = logging.getLogger(__name__)

ALG = "RSA-OAEP-256+A256GCM"


class MeshCryptoEngine:
    def __init__(self):
        if config.MESH_PRIVATE_KEY.strip():
            self._rsa_private_key: rsa.RSAPrivateKey = serialization.load_der_private_key(
                base64.b64decode(config.MESH_PRIVATE_KEY.strip()), password=None
            )
        else:
            log.warning("MESH_PRIVATE_KEY not set; using an ephemeral RSA key (dev only)")
            self._rsa_private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        if config.MESH_RECEIPT_KEY.strip():
            self._ed_private_key: ed25519.Ed25519PrivateKey = ed25519.Ed25519PrivateKey.from_private_bytes(
                base64.b64decode(config.MESH_RECEIPT_KEY.strip())
            )
        else:
            log.warning("MESH_RECEIPT_KEY not set; using an ephemeral Ed25519 key (dev only)")
            self._ed_private_key = ed25519.Ed25519PrivateKey.generate()

    def get_public_key_info(self) -> Dict[str, Any]:
        """Returns SPKI public key and relay limits for offline phones."""
        pub_der = self._rsa_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        ed_pub_bytes = self._ed_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return {
            "version": "mesh-policy-v1.0",
            "alg": ALG,
            "public_key_spki": base64.b64encode(pub_der).decode("utf-8"),
            "receipt_public_key": base64.b64encode(ed_pub_bytes).decode("utf-8"),
            "max_payload_bytes": 1572864,
            "priorities": ["urgent", "normal"],
        }

    def open_envelope(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypts a carried envelope from Phone B.
        Validates AES-GCM additional data (header) against tampering.
        """
        v = envelope.get("v", 1)
        claim_id = envelope.get("claim_id")
        created_at = envelope.get("created_at")
        priority = envelope.get("priority", "normal")
        wrapped_key_b64 = envelope.get("key")
        iv_b64 = envelope.get("iv")
        ct_b64 = envelope.get("ct")

        if not all([claim_id, created_at, wrapped_key_b64, iv_b64, ct_b64]):
            raise ValueError("Malformed mesh envelope: missing required fields")

        # Reconstruct header bytes (bound additional data)
        header_bytes = f"{v}|{claim_id}|{created_at}|{priority}".encode("utf-8")

        wrapped_key = base64.b64decode(wrapped_key_b64)
        iv = base64.b64decode(iv_b64)
        ciphertext = base64.b64decode(ct_b64)

        # 1. Decrypt AES key with RSA-OAEP SHA-256
        aes_key = self._rsa_private_key.decrypt(
            wrapped_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        # 2. Decrypt payload with AES-256-GCM
        aesgcm = AESGCM(aes_key)
        plaintext = aesgcm.decrypt(iv, ciphertext, header_bytes)

        payload = json.loads(plaintext.decode("utf-8"))
        return payload

    def sign_receipt(self, claim_id: str, message: str = "Your claim reached the relief office") -> Dict[str, Any]:
        """
        Signs an official receipt with Ed25519 verifying claim was received.
        """
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        receipt_data = {
            "claim_id": claim_id,
            "created_at": now_iso,
            "message": message,
            "reference": claim_id,
        }
        # Canonical bytes to sign
        canonical = f"{claim_id}|{now_iso}|{message}".encode("utf-8")
        sig = self._ed_private_key.sign(canonical)
        receipt_data["signature"] = base64.b64encode(sig).decode("utf-8")
        return receipt_data


mesh_engine = MeshCryptoEngine()
