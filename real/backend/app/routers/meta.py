"""
System Health and Meta Information Router
"""
from fastapi import APIRouter
from .. import config, entitlement, proofs
from ..db import db

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health_check():
    client = db.get_client()
    return {
        "ok": True,
        "database": "firebase-firestore" if client else "memory-cache",
        "project_id": config.PROJECT_ID,
        "project_number": config.PROJECT_NUMBER,
        "ai_engine": "Google Gemini 3.5 Flash",
        "speech_stt": "Gemini Multilingual Audio",
        "speech_tts": "gTTS Regional",
        "vision_engine": "Gemini 3.5 Flash Vision",
        "languages": config.SUPPORTED_LANGUAGES,
        "mesh_relay": "Active (RSA-OAEP-256 + AES-256-GCM + Ed25519)",
    }


@router.get("/rules/sdrf")
async def get_sdrf_rules():
    return entitlement.load_sdrf_rules()


@router.get("/rules/proofs")
async def get_proof_rules():
    return proofs.load_proof_rules()
