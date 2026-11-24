"""
Speech Audio Generation Router (Listen Button Support)
"""
from fastapi import APIRouter, HTTPException, Response
from .. import tts_service, config
from ..schemas import SpeechRequest

router = APIRouter(tags=["speech"])


@router.post("/speech")
async def read_speech(body: SpeechRequest):
    if body.language not in config.SUPPORTED_LANGUAGES:
        body.language = "en"
    mp3_data = await tts_service.generate_speech(body.text, body.language)
    return Response(
        content=mp3_data,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
