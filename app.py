"""
TTSService - Dedicated Edge TTS Microservice
Compatible with audiobible, audiobook, texttomp3, and other client apps.
"""

import os
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from tts_engine import TTSEngine, DEFAULT_VOICE, SUPPORTED_VOICES

app = FastAPI(
    title="TTSService",
    description="Dedicated Microsoft Edge TTS Microservice with High Availability & Caching",
    version="1.0.0"
)

# Enable CORS for all origins (audiobible, audiobook, texttomp3, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = TTSEngine()

# Static directory for web UI
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = DEFAULT_VOICE
    bookIndex: Optional[int] = None
    chapterIndex: Optional[int] = None
    verseNum: Optional[int] = None
    translation: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint for Watchdog and monitoring tools."""
    return {"status": "ok", "service": "ttsservice", "version": "1.0.0"}


@app.get("/api/voices")
async def list_voices():
    """Returns available high-quality voices including Emma and Korean neural voices."""
    return {"voices": SUPPORTED_VOICES}


@app.post("/api/tts")
async def synthesize_post(req: TTSRequest):
    """
    POST /api/tts
    Compatible with existing texttomp3 / audiobible client payloads:
    { "text": "...", "voice": "en-US-EmmaMultilingualNeural" }
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    voice = req.voice or DEFAULT_VOICE
    try:
        audio_bytes = await engine.synthesize(req.text, voice=voice)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "Access-Control-Allow-Origin": "*",
                "Accept-Ranges": "bytes",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")


@app.get("/api/tts")
async def synthesize_get(
    text: str = Query(..., description="Text to synthesize"),
    voice: str = Query(DEFAULT_VOICE, description="Voice name"),
):
    """
    GET /api/tts?text=...&voice=...
    Fast query-based streaming & caching endpoint.
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        audio_bytes = await engine.synthesize(text, voice=voice)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "Access-Control-Allow-Origin": "*",
                "Accept-Ranges": "bytes",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serves the Audio Studio Web UI."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>TTSService is Running</h1><p>Visit <a href='/docs'>/docs</a> for API documentation.</p>")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8099))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
