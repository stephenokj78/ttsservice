"""
High-Performance Edge TTS Engine
Powered by Microsoft Edge TTS via api.msedgeservices.com
"""

import asyncio
import hashlib
import os
import secrets
import ssl
import time
import uuid
import certifi
import aiohttp
from typing import Optional

TRUSTED_CLIENT_TOKEN = "6A5AA1D4EAFF4E9FB37E23D68491D6F4"
WIN_EPOCH = 11644473600
S_TO_NS = 1e9
CHROMIUM_VERSION = "143.0.3650.75"
SEC_MS_GEC_VERSION = f"1-{CHROMIUM_VERSION}"

DEFAULT_VOICE = "en-US-EmmaMultilingualNeural"

SUPPORTED_VOICES = [
    {"id": "en-US-EmmaMultilingualNeural", "name": "Emma (영어/다국어 여성, 추천)", "lang": "en-US"},
    {"id": "ko-KR-SunHiNeural", "name": "선희 (한국어 여성, 추천)", "lang": "ko-KR"},
    {"id": "ko-KR-InJoonNeural", "name": "인준 (한국어 남성)", "lang": "ko-KR"},
    {"id": "en-US-GuyNeural", "name": "Guy (영어 남성)", "lang": "en-US"},
    {"id": "en-US-JennyNeural", "name": "Jenny (영어 여성)", "lang": "en-US"},
    {"id": "en-US-AndrewMultilingualNeural", "name": "Andrew (영어 남성 다국어)", "lang": "en-US"},
    {"id": "en-US-BrianMultilingualNeural", "name": "Brian (영어 남성 다국어)", "lang": "en-US"},
    {"id": "en-US-AvaMultilingualNeural", "name": "Ava (영어 여성 다국어)", "lang": "en-US"},
]

def generate_sec_ms_gec() -> str:
    """Generates the short-lived Sec-MS-GEC token required by Microsoft TTS."""
    ticks = time.time() + WIN_EPOCH
    ticks -= ticks % 300
    ticks *= S_TO_NS / 100
    str_to_hash = f"{ticks:.0f}{TRUSTED_CLIENT_TOKEN}"
    return hashlib.sha256(str_to_hash.encode("ascii")).hexdigest().upper()


class TTSEngine:
    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.ssl_ctx = ssl.create_default_context(cafile=certifi.where())

    def get_cache_path(self, text: str, voice: str) -> str:
        key = f"{voice}::{text.strip()}".encode("utf-8")
        h = hashlib.sha256(key).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.mp3")

    async def synthesize(self, text: str, voice: str = DEFAULT_VOICE, use_cache: bool = True) -> bytes:
        text = text.strip()
        if not text:
            raise ValueError("Text cannot be empty")

        cache_path = self.get_cache_path(text, voice)
        if use_cache and os.path.exists(cache_path) and os.path.getsize(cache_path) > 300:
            try:
                with open(cache_path, "rb") as f:
                    return f.read()
            except Exception:
                pass

        audio_bytes = await self._synthesize_remote_with_retry(text, voice)

        if use_cache and len(audio_bytes) > 300:
            try:
                with open(cache_path, "wb") as f:
                    f.write(audio_bytes)
            except Exception:
                pass

        return audio_bytes

    async def _synthesize_remote_with_retry(self, text: str, voice: str, retries: int = 3, delay: float = 1.0) -> bytes:
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                return await self._synthesize_remote(text, voice)
            except Exception as e:
                last_err = e
                if attempt < retries:
                    await asyncio.sleep(delay * attempt)
        raise last_err or RuntimeError("TTS synthesis failed after retries")

    async def _synthesize_remote(self, text: str, voice: str) -> bytes:
        sec_ms_gec = generate_sec_ms_gec()
        conn_id = uuid.uuid4().hex
        
        # New Microsoft Endpoint supporting Edge 155
        url = (
            "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
            f"?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}"
            f"&Sec-MS-GEC={sec_ms_gec}"
            f"&Sec-MS-GEC-Version={SEC_MS_GEC_VERSION}"
            f"&ConnectionId={conn_id}"
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{CHROMIUM_VERSION.split('.')[0]}.0.0.0 Safari/537.36 "
                f"Edg/{CHROMIUM_VERSION.split('.')[0]}.0.0.0"
            ),
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Origin": "chrome-extension://jdiccldimpdaibmpdkjnbmckianbfold",
            "Sec-WebSocket-Version": "13",
            "Cookie": f"muid={secrets.token_hex(16).upper()};",
        }

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(url, headers=headers, ssl=self.ssl_ctx) as ws:
                ts = time.strftime("%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)", time.gmtime())
                
                config_payload = (
                    f"X-Timestamp:{ts}\r\n"
                    "Content-Type:application/json; charset=utf-8\r\n"
                    "Path:speech.config\r\n\r\n"
                    '{"context":{"synthesis":{"audio":{"metadataoptions":'
                    '{"sentenceBoundaryEnabled":"false","wordBoundaryEnabled":"false"},'
                    '"outputFormat":"audio-24khz-48kbitrate-mono-mp3"}}}}\r\n'
                )
                await ws.send_str(config_payload)

                escaped_text = (
                    text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&apos;")
                )
                ssml = (
                    f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
                    f"<voice name='{voice}'>{escaped_text}</voice></speak>"
                )
                
                req_id = uuid.uuid4().hex
                ssml_payload = (
                    f"X-RequestId:{req_id}\r\n"
                    "Content-Type:application/ssml+xml\r\n"
                    f"X-Timestamp:{ts}\r\n"
                    "Path:ssml\r\n\r\n"
                    f"{ssml}"
                )
                await ws.send_str(ssml_payload)

                audio_data = bytearray()
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.BINARY:
                        data = msg.data
                        if len(data) >= 2:
                            header_len = int.from_bytes(data[:2], "big")
                            audio_data.extend(data[2 + header_len:])
                    elif msg.type == aiohttp.WSMsgType.TEXT:
                        if "Path:turn.end" in msg.data:
                            break
                    elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                        break

                if not audio_data:
                    raise RuntimeError("No audio received from TTS service")

                return bytes(audio_data)
