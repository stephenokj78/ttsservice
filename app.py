"""
TTSService - Dedicated Edge TTS Microservice (aiohttp.web based)
High performance, zero heavy dependencies, perfectly tuned for Linux/Termux/Windows.
"""

import json
import os
from aiohttp import web

from tts_engine import TTSEngine, DEFAULT_VOICE, SUPPORTED_VOICES

engine = TTSEngine()
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Helper for CORS
def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Range, Authorization",
    }


async def handle_options(request: web.Request) -> web.Response:
    return web.Response(status=204, headers=cors_headers())


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response(
        {"status": "ok", "service": "ttsservice", "version": "1.0.0"},
        headers=cors_headers()
    )


async def handle_voices(request: web.Request) -> web.Response:
    return web.json_response({"voices": SUPPORTED_VOICES}, headers=cors_headers())


async def handle_tts_post(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400, headers=cors_headers())

    text = data.get("text", "").strip()
    voice = data.get("voice") or DEFAULT_VOICE

    if not text:
        return web.json_response({"error": "Text cannot be empty"}, status=400, headers=cors_headers())

    try:
        audio_bytes = await engine.synthesize(text, voice=voice)
        headers = {
            **cors_headers(),
            "Content-Type": "audio/mpeg",
            "Cache-Control": "public, max-age=31536000, immutable",
            "Accept-Ranges": "bytes",
        }
        return web.Response(body=audio_bytes, headers=headers)
    except Exception as e:
        return web.json_response({"error": f"TTS synthesis failed: {str(e)}"}, status=500, headers=cors_headers())


async def handle_tts_get(request: web.Request) -> web.Response:
    text = request.query.get("text", "").strip()
    voice = request.query.get("voice", DEFAULT_VOICE)

    if not text:
        return web.json_response({"error": "Text cannot be empty"}, status=400, headers=cors_headers())

    try:
        audio_bytes = await engine.synthesize(text, voice=voice)
        headers = {
            **cors_headers(),
            "Content-Type": "audio/mpeg",
            "Cache-Control": "public, max-age=31536000, immutable",
            "Accept-Ranges": "bytes",
        }
        return web.Response(body=audio_bytes, headers=headers)
    except Exception as e:
        return web.json_response({"error": f"TTS synthesis failed: {str(e)}"}, status=500, headers=cors_headers())


async def handle_ui(request: web.Request) -> web.Response:
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html")
    return web.Response(text="<h1>TTSService is running</h1>", content_type="text/html")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_options("/{tail:.*}", handle_options)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/api/voices", handle_voices)
    app.router.add_post("/api/tts", handle_tts_post)
    app.router.add_get("/api/tts", handle_tts_get)
    app.router.add_get("/", handle_ui)
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8099))
    web.run_app(create_app(), host="0.0.0.0", port=port)
