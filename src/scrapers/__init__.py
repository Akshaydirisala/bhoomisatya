"""Scraper package – re-exports all scraper classes."""

from src.scrapers.base import BaseScraper
from src.scrapers.dharani import DharaniScraper
from src.scrapers.ecourts import ECourtsScraper
from src.scrapers.igrs import IGRSScraper
from src.scrapers.meebhoomi import MeebhoomiScraper
from src.scrapers.rera_ap import RERAAP
from src.scrapers.rera_telangana import RERATelangana
from src.scrapers.satellite import SatelliteScraper

__all__ = [
    "BaseScraper",
    "DharaniScraper",
    "ECourtsScraper",
    "IGRSScraper",
    "MeebhoomiScraper",
    "RERAAP",
    "RERATelangana",
    "SatelliteScraper",
]
