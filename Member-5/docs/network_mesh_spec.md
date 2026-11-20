# 📡 Network Mesh Store-and-Forward Protocol Specification
## Phone-to-Phone Emergency Claim Relaying for Disaster-Isolated Communities

> **Author:** Member 5 (Entitlement, Policy & Pitch)  
> **Collaborators:** Member 3 (Relay Intake on `/sync`), Member 4 (Android Google Nearby Connections UI), Member 2 (Server Key Pair & Receipts)  
> **Phase:** Roadmap Feature (Phase 2)  
> **Policy Reference:** `Member-5/rules/mesh_policy.json`

---

## 1. Problem & Operational Context

In extreme natural disasters (cyclones, catastrophic flooding, landslides, earthquakes), cellular towers and fiber backhauls are frequently knocked out for 3 to 7 days. While local offline storage (Member 3) allows a victim to draft and store a claim on their phone, that claim cannot reach disaster management authorities if *that specific victim* remains stranded without physical transit to a connected area.

The **Network Mesh Store-and-Forward Protocol** enables mobile devices running Aapke Liye to discover each other locally over Bluetooth Low Energy (BLE) and Wi-Fi Direct, exchanging cryptographically sealed claim envelopes. Stranded victims pass their sealed claims to moving neighbors, rescue boats, or NGO relief teams, until any carrier device regains mobile signal and delivers the queue to the government server.

---

## 2. Store-and-Forward Protocol Architecture

```
[Stranded Victim Phone A] (No Cellular Signal)
        │
        │ 1. Asymmetric Envelope Encryption (Server Public Key)
        ▼
   [Sealed Binary Envelope (.claim.sealed) ≤ 1.5 MB]
        │
        │ 2. Bluetooth LE / Wi-Fi Direct Handshake (Claim-ID List Exchange)
        ▼
[Carrier Phone B (Volunteer / Neighbor)] (No Cellular Signal)
        │
        │ 3. Physical transit toward road / relief camp / mobile tower
        ▼
[Carrier Phone B reaches Cellular Signal (4G/5G/Satellite)]
        │
        │ 4. Batch Delivery via POST /sync
        ▼
[SDMA Government Server (Member 2 & 3)]
        │
        │ 5. Decrypt with Server Private Key + Ed25519 Signed Delivery Receipt
        ▼
[Receipt Carried Back via Mesh to Victim Phone A] ➔ UI updates: "Your claim reached the relief office"
```

---

## 3. Cryptographic Envelope Packaging

To ensure zero intermediate tampering or eavesdropping, claims are packaged using **Hybrid Envelope Encryption**:

1. **Inner Payload:**
   - Structured Claim JSON (1 KB)
   - Compressed Voice Note (Opus codec @ 6 kbps, ~20 KB)
   - Inspection Damage Thumbnail (WebP 480p @ quality 35, ~20 KB)
   - Perceptual Image Hashes (pHash, 64 bytes)
2. **Symmetric Encryption:**
   - The payload is encrypted on the originating device using an ephemeral **AES-256-GCM** key.
3. **Asymmetric Key Encapsulation:**
   - The AES key is wrapped with the State Disaster Management Authority's **RSA-4096 / X25519 Public Key**.
4. **Envelope Outer Header (Unencrypted Metadata):**
   - `claim_id` (UUIDv4)
   - `created_at` (ISO 8601 UTC timestamp)
   - `sender_device_pubkey` (Ed25519 public key of transmitting device)
   - `sender_signature` (Digital signature over header fields to prevent forged envelope spam)
   - `priority_flag`: Coarse binary indicator (`urgent` for fully destroyed shelter/casualties vs. `normal`). Full vulnerability scores are never exposed outside the sealed payload.
   - `payload_size_bytes` (Strictly $\le$ 1.5 MB)

---

## 4. Discovery & Synchronization Protocol

### 4.1 Claim-ID List Exchange (Avoiding Bloom Filter Collisions)
Rather than lossy probabilistic structures (Bloom filters) which experience unacceptably high false-positive skipping at 400 claims, devices perform a deterministic exchange:
1. When two devices connect over BLE/Wi-Fi Direct, Device A sends its list of currently held `claim_id` tokens (≈16 bytes per claim; only 400 bytes for 25 claims).
2. Device B compares the list against its local store and requests only missing IDs.
3. Payloads are transferred sequentially, prioritized by the `urgent` flag.

### 4.2 Storage Ceilings & Life Cycle (TTL)
- **Per-Device Relay Cap:** Maximum **30 MB** (approx. 20–25 claim envelopes). Once the cap is reached, new envelopes are rejected unless marked `urgent` (which evicts the oldest `normal` envelope).
- **Time-to-Live (TTL):** All unacknowledged envelopes expire and are automatically purged after **7 days** (604,800 seconds).
- **Deletion Upon Receipt:** The moment a device receives confirmation that an envelope has reached the server, the encrypted envelope is purged from relay storage to free memory.

### 4.3 Two-Way Reverse Sync (Signed Delivery Receipts)
1. Upon successful ingestion of an envelope via `POST /sync`, the server generates a lightweight **Cryptographic Delivery Receipt** (~100 bytes):
   $$\text{Receipt} = \text{Sign}_{\text{Server}}(\text{claim\_id} + \text{received\_timestamp})$$
2. Carrier phones fetch pending receipts via `GET /sync/receipts?ids=...` and carry them back into the mesh.
3. When the originating victim device receives its matching receipt token, the app UI updates from:
   `"Relaying via Mesh..."` $\rightarrow$ **`"Your claim reached the relief office"`**  
   *(Note: The receipt strictly confirms intake delivery to the relief authority, never approval or payment).*

---

## 5. Battery & Resource Preservation

1. **Strict Battery Floor:** All mesh scanning, broadcasting, and relaying **hard-halts at 25% battery level** (or immediately upon activation of Android Battery Saver mode).
2. **Duty-Cycled Opportunistic Discovery:**
   - BLE scanning is not continuous. It runs for **30 seconds every 15 minutes** (900 seconds sleep).
   - Accelerometer trigger: Scanning temporarily activates for 60 seconds if the device detects sustained physical walking/transit.
3. **Android Platform Requirement:** Background BLE and Wi-Fi Direct store-and-forward operations require a persistent **Android Foreground Service** with an ongoing notification icon ("Aapke Liye Mesh Relay Active").

---

## 6. Privacy & Legal Position (DPDP Act 2023 & IT Act 2000)

### 6.1 The "Mere Conduit" Legal Position
It is our formal position that community devices relaying emergency disaster claims operate strictly as **cryptographic conduits**:
- **Information Technology Act, 2000 (Section 79):** Intermediary protection applies because relay devices have zero knowledge of, and exercise zero editorial control or access to, the contents of the sealed envelope.
- **Digital Personal Data Protection (DPDP) Act, 2023:** Relay phones process only opaque encrypted bytes without access to personal identifiers, biometric files, or plain text. The transmitting device holds no decryption keys.
- **Immediate Erasure:** Envelopes are ephemeral and purged immediately upon receipt of server delivery confirmation or 7-day TTL expiry.

### 6.2 Voluntary Carrier Consent
Mesh relaying is **100% opt-in**. Citizens must affirmatively consent to enable their device as a relay carrier. The plain-language notice is available in all 6 regional languages in `rules/labels.json`.
