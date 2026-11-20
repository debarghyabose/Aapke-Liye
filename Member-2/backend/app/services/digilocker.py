"""
DigiLocker integration service.
DIGILOCKER_MODE=mock (default): returns sample documents with a "Demo: DigiLocker mock" banner.
When the real DigiLocker API is registered (DIGILOCKER_MODE=live), only this file changes.
"""
import os


DIGILOCKER_MODE = os.environ.get("DIGILOCKER_MODE", "mock").strip().lower()

# Sample documents the mock "issues" via the consent flow
MOCK_ISSUED_DOCS = [
    {"doc_type": "aadhaar", "filename": "aadhaar_digilocker_demo.pdf",
     "content_type": "application/pdf"},
    {"doc_type": "ration_card", "filename": "ration_card_digilocker_demo.pdf",
     "content_type": "application/pdf"},
]


def _mock_pdf(doc_type: str) -> bytes:
    """A tiny PDF that says 'Demo: DigiLocker mock' so it is never confused with a real doc."""
    # Minimal valid PDF with the demo banner
    text = f"Demo: DigiLocker mock - {doc_type.replace('_', ' ').title()}"
    stream = text.encode()
    length = len(stream)
    return (
        b"%PDF-1.0\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        + f"4 0 obj<</Length {length + 30}>>\nstream\nBT /F1 12 Tf 10 60 Td ({text}) Tj ET\nendstream\nendobj\n".encode()
        + b"xref\n0 6\ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )


async def start(household_id: str) -> dict:
    """
    Begin the DigiLocker consent flow.
    Mock: returns a consent URL that is really just a callback trigger.
    Real: would return the DigiLocker OAuth authorize URL.
    """
    if DIGILOCKER_MODE != "mock":
        raise NotImplementedError("Real DigiLocker integration not yet available")
    return {
        "mode": "mock",
        "banner": "Demo: DigiLocker mock",
        "consent_url": f"/households/{household_id}/digilocker/callback",
        "message": "In production, this would redirect to DigiLocker's consent screen.",
    }


async def callback(household_id: str) -> list[dict]:
    """
    Complete the consent flow and return the issued documents.
    Mock: returns sample Aadhaar and Ration Card PDFs.
    Real: would exchange the auth code, call /v2/file/issued, fetch each document.
    """
    if DIGILOCKER_MODE != "mock":
        raise NotImplementedError("Real DigiLocker integration not yet available")
    results = []
    for doc_info in MOCK_ISSUED_DOCS:
        results.append({
            "doc_type": doc_info["doc_type"],
            "content_type": doc_info["content_type"],
            "data": _mock_pdf(doc_info["doc_type"]),
            "source": "digilocker_mock",
        })
    return results
