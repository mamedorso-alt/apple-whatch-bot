from __future__ import annotations

import httpx

from app.core.config import get_settings

settings = get_settings()


async def transcribe_telegram_media(file_id: str, fallback_filename: str = "voice.ogg") -> str:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_NOT_CONFIGURED")
    if not settings.openai_api_key:
        raise RuntimeError("VOICE_NOT_CONFIGURED")

    get_file_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getFile"
    async with httpx.AsyncClient(timeout=settings.openai_stt_timeout_sec) as client:
        file_resp = await client.post(get_file_url, json={"file_id": file_id})
        file_resp.raise_for_status()
        file_body = file_resp.json()
        file_path = ((file_body.get("result") or {}).get("file_path") or "").strip()
        if not file_path:
            raise RuntimeError("VOICE_TRANSCRIPTION_FAILED")

        download_url = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}"
        media_resp = await client.get(download_url)
        media_resp.raise_for_status()

        file_name = file_path.rsplit("/", 1)[-1] if "/" in file_path else fallback_filename
        audio_bytes = media_resp.content
        if not audio_bytes:
            raise RuntimeError("VOICE_TRANSCRIPTION_FAILED")

        stt_resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            data={"model": settings.openai_stt_model},
            files={"file": (file_name, audio_bytes, "application/octet-stream")},
        )
        stt_resp.raise_for_status()
        stt_body = stt_resp.json()
        text = (stt_body.get("text") or "").strip()
        if not text:
            raise RuntimeError("VOICE_TRANSCRIPTION_FAILED")
        return text
