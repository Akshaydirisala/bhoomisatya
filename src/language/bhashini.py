"""Bhashini API integration for multilingual speech and translation services."""

from __future__ import annotations

import base64
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

PIPELINE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"


class BhashiniClient:
    """Client for Bhashini AI speech-to-text, text-to-speech, and translation APIs."""

    def __init__(
        self,
        api_key: str,
        user_id: str,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._user_id = user_id
        self._timeout = timeout
        self._headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers=self._headers,
            timeout=self._timeout,
        )

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        source_lang: str = "te",
    ) -> str:
        """Transcribe audio to text using Bhashini ASR.

        Args:
            audio_bytes: Raw audio data (WAV/OGG).
            source_lang: BCP-47 language code (default: 'te' for Telugu).

        Returns:
            Transcribed text string.

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
        """
        log = logger.bind(task="asr", lang=source_lang, audio_size=len(audio_bytes))
        log.info("speech_to_text_started")

        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": source_lang},
                        "audioFormat": "wav",
                        "samplingRate": 16000,
                    },
                }
            ],
            "inputData": {
                "audio": [{"audioContent": audio_b64}],
            },
        }

        async with self._client() as client:
            resp = await client.post(PIPELINE_URL, json=payload)
            resp.raise_for_status()

        result = resp.json()
        try:
            text = result["pipelineResponse"][0]["output"][0]["source"]
        except (KeyError, IndexError) as exc:
            log.error("asr_parse_failed", response=result)
            raise ValueError(f"Unexpected ASR response structure: {result}") from exc

        log.info("speech_to_text_complete", text_length=len(text))
        return text

    async def text_to_speech(
        self,
        text: str,
        target_lang: str = "te",
        gender: str = "female",
    ) -> bytes:
        """Convert text to speech audio using Bhashini TTS.

        Args:
            text: Text to synthesize.
            target_lang: BCP-47 language code (default: 'te').
            gender: Voice gender — 'male' or 'female'.

        Returns:
            Audio bytes (WAV format).

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
        """
        log = logger.bind(task="tts", lang=target_lang, text_length=len(text))
        log.info("text_to_speech_started")

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": target_lang},
                        "gender": gender,
                    },
                }
            ],
            "inputData": {
                "input": [{"source": text}],
            },
        }

        async with self._client() as client:
            resp = await client.post(PIPELINE_URL, json=payload)
            resp.raise_for_status()

        result = resp.json()
        try:
            audio_b64 = result["pipelineResponse"][0]["audio"][0]["audioContent"]
        except (KeyError, IndexError) as exc:
            log.error("tts_parse_failed", response=result)
            raise ValueError(f"Unexpected TTS response structure: {result}") from exc

        audio_bytes = base64.b64decode(audio_b64)
        log.info("text_to_speech_complete", audio_size=len(audio_bytes))
        return audio_bytes

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Translate text between languages using Bhashini NMT.

        Args:
            text: Source text to translate.
            source_lang: Source language code (e.g. 'en').
            target_lang: Target language code (e.g. 'te').

        Returns:
            Translated text string.

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
        """
        log = logger.bind(task="translation", source=source_lang, target=target_lang)
        log.info("translation_started")

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "translation",
                    "config": {
                        "language": {
                            "sourceLanguage": source_lang,
                            "targetLanguage": target_lang,
                        },
                    },
                }
            ],
            "inputData": {
                "input": [{"source": text}],
            },
        }

        async with self._client() as client:
            resp = await client.post(PIPELINE_URL, json=payload)
            resp.raise_for_status()

        result = resp.json()
        try:
            translated = result["pipelineResponse"][0]["output"][0]["target"]
        except (KeyError, IndexError) as exc:
            log.error("translation_parse_failed", response=result)
            raise ValueError(f"Unexpected translation response structure: {result}") from exc

        log.info("translation_complete", output_length=len(translated))
        return translated
