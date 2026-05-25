"""LangChain tools for BhoomiSatya property verification agent."""

from __future__ import annotations

import json
from typing import Optional

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger(__name__)


@tool
async def check_land_records(
    survey_number: str,
    district: str,
    mandal: str,
    village: str,
    state: str,
) -> str:
    """Check land ownership records from Dharani (Telangana) or MeeBhoomi (Andhra Pradesh).

    Retrieves the Record of Rights (RoR / Pahani / Adangal) for the given
    survey number, including current owner name, extent, classification, and
    any mutation history.

    Args:
        survey_number: The survey or plot number of the land parcel.
        district: District name (e.g. 'Rangareddy', 'Guntur').
        mandal: Mandal / sub-district name.
        village: Village name.
        state: 'telangana' or 'andhra_pradesh'.

    Returns:
        JSON string with land record details or an error message.
    """
    log = logger.bind(
        tool="check_land_records",
        survey_number=survey_number,
        district=district,
        state=state,
    )
    try:
        if state.lower() in ("telangana", "ts"):
            from src.scrapers.dharani import DharaniScraper

            scraper = DharaniScraper()
        elif state.lower() in ("andhra_pradesh", "ap", "andhra pradesh"):
            from src.scrapers.meebhoomi import MeebhoomiScraper

            scraper = MeebhoomiScraper()
        else:
            return json.dumps(
                {"error": f"Unsupported state: {state}. Only Telangana and AP are supported."}
            )

        log.info("scraping_land_records")
        result = await scraper.scrape(
            survey_number=survey_number,
            district=district,
            mandal=mandal,
            village=village,
        )
        log.info(
            "land_records_retrieved", record_count=len(result) if isinstance(result, list) else 1
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as exc:
        log.error("land_records_failed", error=str(exc))
        return json.dumps(
            {
                "error": "Land records portal is currently unavailable.",
                "detail": str(exc),
                "source": "dharani" if state.lower() in ("telangana", "ts") else "meebhoomi",
            }
        )


@tool
async def search_rera_project(
    project_name_or_rera_number: str,
    state: str,
) -> str:
    """Search RERA registration status for a real estate project.

    Checks whether a project is registered with the Real Estate Regulatory
    Authority and retrieves registration details, promoter info, project
    timeline, and compliance status.

    Args:
        project_name_or_rera_number: Project name or RERA registration number.
        state: 'telangana' or 'andhra_pradesh'.

    Returns:
        JSON string with RERA project details or an error message.
    """
    log = logger.bind(tool="search_rera_project", query=project_name_or_rera_number, state=state)
    try:
        if state.lower() in ("telangana", "ts"):
            from src.scrapers.rera_telangana import RERATelangana

            scraper = RERATelangana()
        elif state.lower() in ("andhra_pradesh", "ap", "andhra pradesh"):
            from src.scrapers.rera_ap import RERAAP

            scraper = RERAAP()
        else:
            return json.dumps({"error": f"Unsupported state: {state}."})

        log.info("searching_rera")
        result = await scraper.scrape(query=project_name_or_rera_number)
        log.info("rera_search_complete")
        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as exc:
        log.error("rera_search_failed", error=str(exc))
        return json.dumps(
            {
                "error": "RERA portal is currently unavailable.",
                "detail": str(exc),
                "source": f"rera_{state}",
            }
        )


@tool
async def check_court_cases(
    party_name: str,
    state: str,
    district: str,
) -> str:
    """Search eCourts for any active or disposed court cases involving a party.

    Looks up civil and criminal cases by party name in the specified district
    court. Useful for detecting litigation risk on a property or its owner.

    Args:
        party_name: Name of the property owner or party to search.
        state: State name (e.g. 'telangana', 'andhra_pradesh').
        district: District where the court is located.

    Returns:
        JSON string with case details or an error message.
    """
    log = logger.bind(tool="check_court_cases", party_name=party_name, district=district)
    try:
        from src.scrapers.ecourts import ECourtsScraper

        scraper = ECourtsScraper()
        log.info("searching_court_cases")
        result = await scraper.scrape(
            party_name=party_name,
            state=state,
            district=district,
        )
        log.info("court_cases_retrieved", case_count=len(result) if isinstance(result, list) else 0)
        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as exc:
        log.error("court_cases_failed", error=str(exc))
        return json.dumps(
            {
                "error": "eCourts portal is currently unavailable.",
                "detail": str(exc),
                "source": "ecourts",
            }
        )


@tool
async def check_encumbrance(
    survey_number: str,
    district: str,
    village: str,
    state: str,
    from_year: int,
    to_year: int,
) -> str:
    """Check encumbrance certificate data for a property.

    Retrieves the encumbrance certificate (EC) showing all registered
    transactions — sales, mortgages, liens, releases — on the property
    within the specified period.

    Args:
        survey_number: Survey or plot number.
        district: District name.
        village: Village name.
        state: 'telangana' or 'andhra_pradesh'.
        from_year: Start year for the EC search period.
        to_year: End year for the EC search period.

    Returns:
        JSON string with encumbrance details or an error message.
    """
    log = logger.bind(
        tool="check_encumbrance",
        survey_number=survey_number,
        district=district,
        period=f"{from_year}-{to_year}",
    )
    try:
        from src.scrapers.igrs import IGRSScraper

        scraper = IGRSScraper(state=state)
        log.info("checking_encumbrance")
        result = await scraper.scrape(
            task="encumbrance",
            survey_number=survey_number,
            district=district,
            village=village,
            from_year=from_year,
            to_year=to_year,
        )
        log.info("encumbrance_retrieved")
        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as exc:
        log.error("encumbrance_failed", error=str(exc))
        return json.dumps(
            {
                "error": "IGRS portal is currently unavailable for encumbrance search.",
                "detail": str(exc),
                "source": "igrs",
            }
        )


@tool
async def get_valuation_data(
    district: str,
    mandal: str,
    village: str,
    state: str,
) -> str:
    """Get government guideline values and comparable sales data for a locality.

    Retrieves the official guideline/circle rate value per unit area and
    recent comparable registered sale transactions in the same village/mandal.
    Used for fair market value estimation.

    Args:
        district: District name.
        mandal: Mandal / sub-district name.
        village: Village name.
        state: 'telangana' or 'andhra_pradesh'.

    Returns:
        JSON string with guideline values and comparable sales or an error.
    """
    log = logger.bind(tool="get_valuation_data", district=district, mandal=mandal, village=village)
    try:
        from src.scrapers.igrs import IGRSScraper

        scraper = IGRSScraper(state=state)
        log.info("fetching_valuation_data")
        result = await scraper.scrape(
            task="valuation",
            district=district,
            mandal=mandal,
            village=village,
        )
        log.info("valuation_data_retrieved")
        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as exc:
        log.error("valuation_data_failed", error=str(exc))
        return json.dumps(
            {
                "error": "IGRS portal is currently unavailable for valuation data.",
                "detail": str(exc),
                "source": "igrs",
            }
        )


@tool
async def get_satellite_image(
    village: str,
    mandal: str,
    district: str,
    state: str,
) -> str:
    """Retrieve satellite imagery and land-use classification for a location.

    Fetches recent satellite data for the specified village, including
    land-use classification (agricultural, residential, barren, water body)
    and boundary information useful for physical verification.

    Args:
        village: Village name.
        mandal: Mandal / sub-district name.
        district: District name.
        state: 'telangana' or 'andhra_pradesh'.

    Returns:
        JSON string with satellite data URLs and classification or an error.
    """
    log = logger.bind(tool="get_satellite_image", village=village, district=district)
    try:
        from src.scrapers.satellite import SatelliteScraper

        scraper = SatelliteScraper()
        log.info("fetching_satellite_data")
        result = await scraper.scrape(
            village=village,
            mandal=mandal,
            district=district,
            state=state,
        )
        log.info("satellite_data_retrieved")
        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as exc:
        log.error("satellite_data_failed", error=str(exc))
        return json.dumps(
            {
                "error": "Satellite imagery service is currently unavailable.",
                "detail": str(exc),
                "source": "satellite",
            }
        )


@tool
async def generate_report(report_id: str) -> str:
    """Generate a PDF verification report for a completed property analysis.

    Triggers PDF generation using the stored analysis data for the given
    report ID. The PDF includes safety score, findings, valuation analysis,
    satellite imagery, and recommendations.

    Args:
        report_id: Unique identifier for the verification report.

    Returns:
        JSON string with the report file path/URL or an error message.
    """
    log = logger.bind(tool="generate_report", report_id=report_id)
    try:
        from src.agent.report_generator import generate_pdf, save_report

        log.info("generating_pdf_report")
        # Report data would be fetched from a store keyed by report_id.
        # For now we assume it's available in a shared state/store.
        from src.agent._state_store import get_report_data

        report_data = await get_report_data(report_id)
        if not report_data:
            return json.dumps({"error": f"No data found for report_id: {report_id}"})

        pdf_bytes = await generate_pdf(report_data)
        file_path = await save_report(report_id, pdf_bytes)
        log.info("report_generated", path=file_path)
        return json.dumps({"report_id": report_id, "file_path": file_path, "status": "generated"})

    except Exception as exc:
        log.error("report_generation_failed", error=str(exc))
        return json.dumps(
            {
                "error": "Failed to generate PDF report.",
                "detail": str(exc),
            }
        )
