"""Shared pytest fixtures for BhoomiSatya test suite."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client wired to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_whatsapp_text_payload() -> dict:
    """Sample WhatsApp Cloud API text message payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "919999999999",
                                "phone_number_id": "phone_id_123",
                            },
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "msg_001",
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {
                                        "body": "Check survey number 45, Shamshabad, Rangareddy"
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_whatsapp_audio_payload() -> dict:
    """Sample WhatsApp Cloud API audio message payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "919999999999",
                                "phone_number_id": "phone_id_123",
                            },
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "msg_002",
                                    "timestamp": "1700000001",
                                    "type": "audio",
                                    "audio": {
                                        "id": "audio_media_id_001",
                                        "mime_type": "audio/ogg; codecs=opus",
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_razorpay_payload() -> dict:
    """Sample Razorpay payment.captured webhook payload."""
    return {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test123",
                    "amount": 199900,
                    "currency": "INR",
                    "status": "captured",
                    "method": "upi",
                    "notes": {
                        "report_id": "rpt_test_001",
                        "report_type": "full",
                    },
                }
            }
        },
    }
