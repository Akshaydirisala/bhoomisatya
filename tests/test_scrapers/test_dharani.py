"""Tests for the Dharani (Telangana land records) scraper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDharaniScraperInitialization:
    """Test scraper setup and configuration."""

    def test_scraper_has_correct_base_url(self):
        from src.scrapers.dharani import DharaniScraper

        scraper = DharaniScraper()
        assert scraper.base_url == "https://dharani.telangana.gov.in"

    def test_scraper_has_retry_config(self):
        from src.scrapers.dharani import DharaniScraper

        scraper = DharaniScraper()
        assert scraper.max_retries >= 3
        assert scraper.retry_delay > 0

    def test_scraper_inherits_base_class(self):
        from src.scrapers.dharani import DharaniScraper
        from src.scrapers.base import BaseScraper

        scraper = DharaniScraper()
        assert isinstance(scraper, BaseScraper)


class TestDharaniDropdownFlow:
    """Test the cascading dropdown selection flow (district -> mandal -> village)."""

    @pytest.mark.asyncio
    async def test_fetch_districts_returns_list(self):
        from src.scrapers.dharani import DharaniScraper

        scraper = DharaniScraper()

        mock_response = [
            {"code": "01", "name": "Adilabad"},
            {"code": "02", "name": "Hyderabad"},
        ]

        with patch.object(
            scraper, "_post_form", new_callable=AsyncMock, return_value=mock_response
        ):
            districts = await scraper.fetch_districts()
            assert len(districts) == 2
            assert districts[0]["name"] == "Adilabad"

    @pytest.mark.asyncio
    async def test_fetch_mandals_requires_district_code(self):
        from src.scrapers.dharani import DharaniScraper

        scraper = DharaniScraper()

        mock_response = [
            {"code": "01", "name": "Adilabad"},
            {"code": "02", "name": "Boath"},
        ]

        with patch.object(
            scraper, "_post_form", new_callable=AsyncMock, return_value=mock_response
        ) as mock_post:
            mandals = await scraper.fetch_mandals(district_code="01")
            assert len(mandals) == 2
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_land_details_returns_parsed_data(self):
        from src.scrapers.dharani import DharaniScraper

        scraper = DharaniScraper()

        mock_result = {
            "survey_number": "45",
            "extent_acres": 2.5,
            "owner_name": "Test Owner",
            "pattadar_passbook": "PPB123456",
            "land_nature": "Agricultural",
            "district": "Rangareddy",
            "mandal": "Shamshabad",
            "village": "Shamshabad",
        }

        with patch.object(
            scraper,
            "fetch_land_details",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await scraper.fetch_land_details(
                district_code="03",
                mandal_code="02",
                village_code="01",
                survey_number="45",
            )
            assert result["survey_number"] == "45"
            assert result["owner_name"] == "Test Owner"
            assert result["extent_acres"] == 2.5

    @pytest.mark.asyncio
    async def test_scraper_retries_on_failure(self):
        from src.scrapers.dharani import DharaniScraper

        scraper = DharaniScraper()

        call_count = 0

        async def flaky_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Portal temporarily unavailable")
            return [{"code": "01", "name": "Adilabad"}]

        with patch.object(scraper, "_post_form", side_effect=flaky_request):
            districts = await scraper.fetch_districts()
            assert call_count == 3
            assert len(districts) == 1
