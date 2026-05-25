"""WhatsApp Cloud API client for BhoomiSatya."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

BASE_URL = "https://graph.facebook.com/v21.0"


class WhatsAppClient:
    """Client for sending and receiving WhatsApp messages via the Cloud API."""

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        verify_token: str,
        app_secret: str,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._phone_number_id = phone_number_id
        self._access_token = access_token
        self._verify_token = verify_token
        self._app_secret = app_secret
        self._timeout = timeout
        self._messages_url = f"{BASE_URL}/{phone_number_id}/messages"
        self._media_url = f"{BASE_URL}"
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Webhook verification
    # ------------------------------------------------------------------

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str:
        """Verify the WhatsApp webhook subscription request.

        Args:
            mode: hub.mode query parameter (should be 'subscribe').
            token: hub.verify_token query parameter.
            challenge: hub.challenge query parameter.

        Returns:
            The challenge string if verification succeeds.

        Raises:
            ValueError: If mode or token is invalid.
        """
        if mode == "subscribe" and token == self._verify_token:
            logger.info("webhook_verified")
            return challenge
        logger.warning("webhook_verification_failed", mode=mode)
        raise ValueError("Invalid verify token or mode.")

    # ------------------------------------------------------------------
    # Signature validation
    # ------------------------------------------------------------------

    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Validate the X-Hub-Signature-256 header using HMAC-SHA256.

        Args:
            payload: Raw request body bytes.
            signature: Value of the X-Hub-Signature-256 header (sha256=...).

        Returns:
            True if the signature is valid.
        """
        expected = (
            "sha256="
            + hmac.new(
                self._app_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()
        )
        valid = hmac.compare_digest(expected, signature)
        if not valid:
            logger.warning("invalid_webhook_signature")
        return valid

    # ------------------------------------------------------------------
    # Message parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_message(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Extract sender phone, message type, and content from a webhook payload.

        Args:
            payload: Parsed JSON body from WhatsApp webhook POST.

        Returns:
            Dict with keys: sender, type ('text'|'audio'|'image'), body,
            media_id (if applicable), message_id. Returns None if the
            payload does not contain a user message.
        """
        try:
            entry = payload["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]
            messages = value.get("messages")
            if not messages:
                return None

            msg = messages[0]
            sender = msg["from"]
            msg_type = msg["type"]
            message_id = msg["id"]

            result: dict[str, Any] = {
                "sender": sender,
                "type": msg_type,
                "message_id": message_id,
                "body": None,
                "media_id": None,
            }

            if msg_type == "text":
                result["body"] = msg["text"]["body"]
            elif msg_type == "audio":
                result["media_id"] = msg["audio"]["id"]
            elif msg_type == "image":
                result["media_id"] = msg["image"]["id"]
                result["body"] = msg.get("image", {}).get("caption")

            return result

        except (KeyError, IndexError):
            logger.warning("unparseable_webhook_payload")
            return None

    # ------------------------------------------------------------------
    # Sending messages
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=self._headers, timeout=self._timeout)

    async def send_text(self, to: str, text: str) -> dict[str, Any]:
        """Send a text message.

        Args:
            to: Recipient phone number in international format (e.g. '919876543210').
            text: Message body.

        Returns:
            WhatsApp API response dict.
        """
        log = logger.bind(action="send_text", to=to)
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        async with self._client() as client:
            resp = await client.post(self._messages_url, json=payload)
            resp.raise_for_status()
        log.info("text_sent")
        return resp.json()

    async def send_document(
        self,
        to: str,
        document_url: str,
        caption: str,
        filename: str,
    ) -> dict[str, Any]:
        """Send a document (e.g. PDF report).

        Args:
            to: Recipient phone number.
            document_url: Public URL of the document.
            caption: Caption text shown with the document.
            filename: Filename shown to the user.

        Returns:
            WhatsApp API response dict.
        """
        log = logger.bind(action="send_document", to=to, filename=filename)
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {
                "link": document_url,
                "caption": caption,
                "filename": filename,
            },
        }
        async with self._client() as client:
            resp = await client.post(self._messages_url, json=payload)
            resp.raise_for_status()
        log.info("document_sent")
        return resp.json()

    async def send_audio(self, to: str, audio_url: str) -> dict[str, Any]:
        """Send an audio message (voice reply).

        Args:
            to: Recipient phone number.
            audio_url: Public URL of the audio file.

        Returns:
            WhatsApp API response dict.
        """
        log = logger.bind(action="send_audio", to=to)
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "audio",
            "audio": {"link": audio_url},
        }
        async with self._client() as client:
            resp = await client.post(self._messages_url, json=payload)
            resp.raise_for_status()
        log.info("audio_sent")
        return resp.json()

    async def download_media(self, media_id: str) -> bytes:
        """Download media (e.g. voice note) from WhatsApp.

        Two-step process: first retrieve the media URL, then download the file.

        Args:
            media_id: WhatsApp media ID from the incoming message.

        Returns:
            Raw media bytes.
        """
        log = logger.bind(action="download_media", media_id=media_id)
        async with self._client() as client:
            # Step 1: Get media URL
            meta_resp = await client.get(f"{self._media_url}/{media_id}")
            meta_resp.raise_for_status()
            media_url = meta_resp.json()["url"]

            # Step 2: Download the actual file
            dl_resp = await client.get(media_url)
            dl_resp.raise_for_status()

        log.info("media_downloaded", size=len(dl_resp.content))
        return dl_resp.content

    async def send_template(
        self,
        to: str,
        template_name: str,
        parameters: list[str],
        language_code: str = "en",
    ) -> dict[str, Any]:
        """Send a pre-approved template message (e.g. payment link).

        Args:
            to: Recipient phone number.
            template_name: Approved template name.
            parameters: List of parameter values to fill in the template.
            language_code: Template language code.

        Returns:
            WhatsApp API response dict.
        """
        log = logger.bind(action="send_template", to=to, template=template_name)
        components = []
        if parameters:
            components.append(
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in parameters],
                }
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }
        async with self._client() as client:
            resp = await client.post(self._messages_url, json=payload)
            resp.raise_for_status()
        log.info("template_sent")
        return resp.json()
