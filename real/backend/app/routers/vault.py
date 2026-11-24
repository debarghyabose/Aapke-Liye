"""
Household Document Vault & DigiLocker Integration Router
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from .. import id_gen, image_storage
from ..db import db

router = APIRouter(tags=["vault"])


def _get_household_with_auth(household_id: str, x_household_token: Optional[str] = Header(None)) -> Dict[str, Any]:
    hh = db.get_household(household_id)
    if not hh:
        raise HTTPException(404, "Household not found")
    token_hash = hh.get("token_hash")
    if token_hash and x_household_token:
        if not id_gen.verify_token(x_household_token, token_hash):
            raise HTTPException(403, "Invalid household token")
    return hh


@router.post("/households", status_code=201)
async def create_household():
    hh_id = id_gen.generate_household_id()
    token = id_gen.new_token()
    token_hash = id_gen.hash_token(token)
    now_iso = datetime.now(timezone.utc).isoformat()

    hh_data = {
        "household_id": hh_id,
        "token_hash": token_hash,
        "created_at": now_iso,
        "updated_at": now_iso,
        "documents": [],
    }

    db.save_household(hh_id, hh_data)
    db.log_audit(None, "household_created", household_id=hh_id)
    return {"household_id": hh_id, "household_token": token}


@router.get("/households/{household_id}")
async def get_household(household_id: str, x_household_token: Optional[str] = Header(None)):
    hh = _get_household_with_auth(household_id, x_household_token)
    return hh


@router.get("/households/{household_id}/documents")
async def list_household_documents(household_id: str, x_household_token: Optional[str] = Header(None)):
    hh = _get_household_with_auth(household_id, x_household_token)
    return hh.get("documents", [])


@router.post("/households/{household_id}/documents", status_code=201)
async def upload_document(
    household_id: str,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    x_household_token: Optional[str] = Header(None),
):
    hh = _get_household_with_auth(household_id, x_household_token)
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    url, path = await image_storage.storage_service.save_image(
        file_bytes, file.filename or "doc.jpg", content_type, folder="vault"
    )

    doc_id = str(uuid.uuid4().hex[:8])
    doc_entry = {
        "id": doc_id,
        "doc_type": doc_type,
        "content_type": content_type,
        "source": "upload",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file_url": url,
        "path": path,
    }

    hh["documents"].append(doc_entry)
    db.save_household(household_id, hh)
    db.log_audit(None, "vault_doc_uploaded", household_id=household_id, doc_type=doc_type)
    return doc_entry


@router.delete("/households/{household_id}/documents/{doc_id}")
async def delete_document(
    household_id: str,
    doc_id: str,
    x_household_token: Optional[str] = Header(None),
):
    hh = _get_household_with_auth(household_id, x_household_token)
    hh["documents"] = [d for d in hh.get("documents", []) if str(d.get("id")) != str(doc_id)]
    db.save_household(household_id, hh)
    return {"ok": True}


@router.get("/households/{household_id}/documents/{doc_id}/file")
async def get_document_file(
    household_id: str,
    doc_id: str,
    x_household_token: Optional[str] = Header(None),
):
    hh = _get_household_with_auth(household_id, x_household_token)
    doc = next((d for d in hh.get("documents", []) if str(d.get("id")) == str(doc_id)), None)
    if not doc:
        raise HTTPException(404, "Document not found")

    file_bytes = await image_storage.storage_service.read_file(doc.get("path") or doc.get("file_url"))
    return Response(content=file_bytes, media_type=doc.get("content_type", "image/jpeg"))


# --- DigiLocker Mock Consent Integration ---

@router.get("/households/{household_id}/digilocker/start")
async def start_digilocker(household_id: str):
    hh = db.get_household(household_id)
    if not hh:
        raise HTTPException(404, "Household not found")
    consent_url = f"/digilocker/consent?household_id={household_id}"
    return {
        "consent_url": consent_url,
        "banner": "DigiLocker Mock (Pre-disaster document retrieval)",
    }


@router.get("/digilocker/consent")
async def digilocker_consent_page(household_id: str):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>DigiLocker Consent — Aapke Liye</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; padding: 2rem; display: flex; justify-content: center; }}
            .card {{ background: white; border-radius: 12px; padding: 2rem; max-width: 480px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
            .badge {{ background: #e0f2fe; color: #0369a1; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 12px; }}
            h2 {{ color: #0f172a; margin-top: 1rem; }}
            p {{ color: #475569; font-size: 14px; line-height: 1.5; }}
            .btn {{ display: block; width: 100%; text-align: center; background: #2563eb; color: white; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 1rem; }}
        </style>
    </head>
    <body>
        <div class="card">
            <span class="badge">Official DigiLocker Gateway (Demo Mode)</span>
            <h2>Disaster Document Vault Sync</h2>
            <p>You are granting <b>Aapke Liye</b> secure permission to fetch verified demographic credentials (Aadhaar & NFSA Ration Card) directly into your disaster preparedness vault.</p>
            <p>Household ID: <code>{household_id}</code></p>
            <a href="/digilocker/callback?household_id={household_id}" class="btn">Allow & Import Verified Records</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/digilocker/callback")
async def digilocker_callback(household_id: str):
    hh = db.get_household(household_id)
    if not hh:
        raise HTTPException(404, "Household not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    # Add verified mock documents
    sample_docs = [
        {
            "id": "dl-aadhaar-" + uuid.uuid4().hex[:6],
            "doc_type": "aadhaar",
            "content_type": "application/pdf",
            "source": "digilocker_mock",
            "created_at": now_iso,
            "file_url": "/static/sample_aadhaar.pdf",
        },
        {
            "id": "dl-ration-" + uuid.uuid4().hex[:6],
            "doc_type": "ration_card",
            "content_type": "application/pdf",
            "source": "digilocker_mock",
            "created_at": now_iso,
            "file_url": "/static/sample_ration.pdf",
        },
    ]

    existing_types = {d.get("doc_type") for d in hh.get("documents", [])}
    for doc in sample_docs:
        if doc["doc_type"] not in existing_types:
            hh["documents"].append(doc)

    db.save_household(household_id, hh)
    db.log_audit(None, "digilocker_imported", household_id=household_id)
    return RedirectResponse(url="/prepare")


@router.post("/households/{household_id}/digilocker/mock")
async def digilocker_mock_api(household_id: str):
    hh = db.get_household(household_id)
    if not hh:
        raise HTTPException(404, "Household not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    sample_docs = [
        {
            "id": "dl-aadhaar-" + uuid.uuid4().hex[:6],
            "doc_type": "aadhaar",
            "content_type": "application/pdf",
            "source": "digilocker_mock",
            "created_at": now_iso,
            "file_url": "/static/sample_aadhaar.pdf",
        },
        {
            "id": "dl-ration-" + uuid.uuid4().hex[:6],
            "doc_type": "ration_card",
            "content_type": "application/pdf",
            "source": "digilocker_mock",
            "created_at": now_iso,
            "file_url": "/static/sample_ration.pdf",
        },
    ]

    existing_types = {d.get("doc_type") for d in hh.get("documents", [])}
    added = []
    for doc in sample_docs:
        if doc["doc_type"] not in existing_types:
            hh["documents"].append(doc)
            added.append(doc)

    db.save_household(household_id, hh)
    return added
