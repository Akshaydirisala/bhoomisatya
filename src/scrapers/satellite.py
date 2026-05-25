"""Satellite imagery and geocoding helper (Google Maps APIs).

Not a BaseScraper subclass – uses plain httpx for REST calls.
Requires GOOGLE_MAPS_API_KEY in environment / config.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

log = structlog.get_logger()

STATIC_MAP_URL = "https://maps.googleapis.com/maps/api/staticmap"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class SatelliteScraper:
    """Fetch satellite imagery and geocode Indian addresses via Google Maps APIs."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def get_satellite_image(
        self,
        *,
        latitude: float,
        longitude: float,
        zoom: int = 18,
        size: str = "600x400",
    ) -> dict[str, Any]:
        """Return the Static Maps URL and metadata for the given coordinates."""
        params = {
            "center": f"{latitude},{longitude}",
            "zoom": str(zoom),
            "size": size,
            "maptype": "satellite",
            "key": self.api_key,
        }
        url = f"{STATIC_MAP_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        log.info("satellite.url_generated", lat=latitude, lng=longitude)
        return {
            "image_url": url,
            "latitude": latitude,
            "longitude": longitude,
            "zoom": zoom,
            "size": size,
        }

    async def geocode(
        self,
        *,
        village: str,
        mandal: str,
        district: str,
        state: str = "India",
    ) -> dict[str, Any]:
        """Convert an Indian address (village, mandal, district) to lat/lng."""
        address = f"{village}, {mandal}, {district}, {state}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                GEOCODE_URL,
                params={"address": address, "key": self.api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            log.warning("satellite.geocode_failed", address=address, status=data.get("status"))
            return {"latitude": None, "longitude": None, "formatted_address": None}

        location = data["results"][0]["geometry"]["location"]
        return {
            "latitude": location["lat"],
            "longitude": location["lng"],
            "formatted_address": data["results"][0].get("formatted_address", ""),
        }
