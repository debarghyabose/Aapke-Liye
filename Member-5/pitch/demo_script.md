# 🎙️ Live Demo Script (3-Minute Competition Presentation)
## Startup Buildathon India 2026 · Team OPUS

> **Total Duration:** Exactly 180 seconds (3:00 minutes)  
> **Presenter:** Member 5 (Pitch & Policy Lead) with Member 4 (Device Operator)  
> **Tone:** Urgent, Empathetic, Authoritative, Technologically Confident

---

## ⏱️ Timeline & Stage Cues

### [0:00 – 0:30] The Hook: The Forgotten Victim
*(Stage Action: Member 5 stands center stage holding a submerged, waterlogged, illegible paper form in hand.)*

**Member 5:**
> "Respected judges. Imagine you are Ramesh Mandal from Gosaba in the Sundarbans. Last night, Cyclone Remal breached the river embankment. Your kutcha house is underwater. Your 2 goats are dead. And the flood washed away your steel trunk—along with your ration card, your land deeds, and your Aadhaar slip.
> 
> Today, the government announces thousands of crores in relief. Ramesh walks 8 miles to the block office. The clerk asks him to fill a 6-page English form, produce original deeds, and return with photocopies. 
> Ramesh cannot read. He has no papers. And so, like millions of disaster victims across India, Ramesh receives exactly zero rupees.
> 
> We are Team OPUS from IEM Kolkata, and this is **Aapke Liye**."

---

### [0:30 – 1:15] The Live Voice Demonstration (Screen 1 & 2)
*(Stage Action: Member 4 casts phone screen to main projector. The Aapke Liye app appears with 6 regional language buttons.)*

**Member 5:**
> "Watch how simple this is. Ramesh does not read or write English. He taps **Bengali**."

*(Member 4 taps 'Bengali'. Spoken consent audio plays in clear Bengali: 'আমি সম্মত হচ্ছি...')*

**Member 5:**
> "Notice that? Under India's **DPDP Act 2023**, plain-language voice consent is collected first. Now Ramesh simply holds down the microphone and speaks in his own words."

*(Member 4 plays sample audio or speaks into mic in Bengali:  
'আমার নাম রমেশ মণ্ডল, গোসাবা গ্রামে থাকি। ঝড়ে আমার মাতির বাড়িটা ভেঙে গেছে, আর দুটো ছাগল মারা গেছে। দলিল সব ভেসে গেছে।')*

**Member 5:**
> "While Ramesh speaks, Member 1's Whisper AI transcribes the regional audio locally. Then, our extraction pipeline structures the spoken words into clean administrative data: Name: Ramesh Mandal. Location: Gosaba. Losses: Destroyed kutcha house, 2 goats. Documents lost: All."

---

### [1:15 – 1:50] Proof Alternatives & Two-Tier Entitlement (Screen 3 & 4)
*(Stage Action: Member 4 snaps photo of damaged structure.)*

**Member 5:**
> "Now, Ramesh points his camera at the collapsed roof.
> Member 3's computer vision verifies the structural damage score. Our geo-verification extracts the tamper-proof GPS coordinates and timestamp, verifying Ramesh was physically present in the cyclone zone.
> 
> And what about the lost documents? Look at this screen!
> Under Section 12 of the **Disaster Management Act 2005**, our **Proof Substitution Engine** informs Ramesh: *'No Aadhaar? Your Gram Panchayat Pradhan certificate or electronic ration dealer record is legally accepted.'*
> 
> And look at how we display the money: we never over-promise or blend numbers into one false total. We show two transparent blocks:  
> 1. **Relief Owed (SDRF Estimate): ₹1,33,000** — calculated strictly from Ministry of Home Affairs SDRF norms.  
> 2. **You May Also Qualify For (Subject to Eligibility):** PMAY-G Permanent Housing Rebuild (₹1,56,750), clearly listing the condition that Ramesh must be on the rural Awaas+ list.
> 
> Ramesh taps Confirm."

*(Member 4 taps 'Confirm & Generate Relief Claim'.)*

---

### [1:50 – 2:20] The 30-Second Network Mesh Demo (Offline Hand-Off)
*(Stage Action: Member 5 brings out a second phone — Phone B, representing a volunteer / rescue worker.)*

**Member 5:**
> "Now here is our breakthrough. What happens when the cellular towers are destroyed and the village has no signal for 5 days?
> 
> Look at Phone A: **Airplane Mode is ON. Zero bars.**
> Ramesh taps 'Submit via Community Mesh'. Phone A seals the claim into an encrypted 40 KB binary envelope using the government's public key. Phone A discovers Phone B over Bluetooth Low Energy.
> 
> Watch: in 2 seconds, the sealed envelope hops to Phone B.
> Phone B's owner cannot read Ramesh's photos or name—it is completely sealed.
> Now, Phone B walks out of the village toward the main highway."

*(Stage Action: Member 5 toggles Phone B's Cellular Data ON.)*

**Member 5:**
> "The instant Phone B hits LTE, look at the laptop projector! The SDMA Dashboard beeps: **Claim CLM-2026-WB-8921 received via Mesh Relay.**
> And the server sends back an Ed25519 cryptographic receipt. When Phone B returns to the village, Phone A's screen automatically flips to: **'Your claim reached the relief office'**."

---

### [2:20 – 3:00] The Government Heatmap & The Vision
*(Stage Action: Switch laptop display to the SDMA Operations Dashboard.)*

**Member 5:**
> "Finally, look at what the District Magistrate sees:
> A live village damage heatmap, an algorithmic Vulnerability Priority Index routing inspectors to widows and infants first, and a one-click PFMS export for direct bank transfer.
> 
> And if officials stall for 30 days without food or shelter relief? Our legal engine invokes the **Life & Liberty 48-Hour emergency proviso under Section 7(1) of the RTI Act 2005**.
> 
> Free for victims. A high-efficiency B2G SaaS deployment for State Governments.
> 
> Disasters can take a home. They can take documents. But with **Aapke Liye**, they will never take away rightful relief.
> 
> Thank you."

---

## 🎯 Anticipated Judge Q&A Cheat Sheet

### Q1: "How do you prevent fraudulent claims if documents are lost?"
**Answer:**  
*"Three layers of cryptographic defense: First, Member 3's perceptual hashing (pHash) detects if the same photo is reused across claims. Second, EXIF GPS and timestamp verification confirms the photo was taken inside the declared disaster zone during the storm window. Third, the SDMA dashboard cross-references the coordinates against ISRO Bhuvan and Sentinel-1 satellite flood inundation masks."*

### Q2: "What if intermediate phones in the mesh tamper with or steal claims?"
**Answer:**  
*"Mathematically impossible. We use Hybrid Envelope Encryption: the payload is encrypted with AES-256-GCM and wrapped with the SDMA server's RSA-4096 public key. Intermediary phones hold only an opaque binary envelope. They possess no decryption keys, cannot read transcripts or photos, and under Section 79 of the IT Act, operate strictly as mere cryptographic conduits."*

### Q3: "Doesn't mesh relaying drain rural phone batteries in a power outage?"
**Answer:**  
*"No. Scanning is strictly duty-cycled: only 30 seconds every 15 minutes, or on accelerometer motion. The entire mesh hard-halts if battery drops below 25% or if Android Battery Saver mode activates."*
