#!/usr/bin/env python3
"""Quick connectivity test for all government portals used by BhoomiSatya.

Usage:
    python -m scripts.test_portals
"""

import asyncio
import time

import httpx

PORTALS = [
    ("Dharani (Telangana Land Records)", "https://dharani.telangana.gov.in"),
    ("IGRS Telangana (Encumbrance)", "https://registration.telangana.gov.in"),
    ("TS-RERA (Telangana RERA)", "https://rera.telangana.gov.in"),
    ("AP Meebhoomi (AP Land Records)", "https://meebhoomi.ap.gov.in"),
    ("AP IGRS (AP Registration)", "https://registration.ap.gov.in"),
    ("AP-RERA", "https://rera.ap.gov.in"),
    ("CERSAI (Central Mortgage Registry)", "https://www.cersai.org.in"),
    ("MOEF Parivesh (Environmental)", "https://parivesh.nic.in"),
    ("NHAI (Highway Alignment)", "https://nhai.gov.in"),
    ("HMDA (Hyderabad Planning)", "https://www.hmda.gov.in"),
    ("GHMC (Municipal Records)", "https://www.ghmc.gov.in"),
    ("MCA21 (Company Registry)", "https://www.mca.gov.in"),
]


async def check_portal(client: httpx.AsyncClient, name: str, url: str) -> dict:
    """Check a single portal and return result dict."""
    start = time.perf_counter()
    try:
        resp = await client.get(url, follow_redirects=True)
        elapsed = time.perf_counter() - start
        return {
            "name": name,
            "url": url,
            "status": resp.status_code,
            "time_ms": round(elapsed * 1000),
            "ok": 200 <= resp.status_code < 400,
        }
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return {
            "name": name,
            "url": url,
            "status": None,
            "time_ms": round(elapsed * 1000),
            "ok": False,
            "error": str(exc),
        }


async def main():
    print("=" * 80)
    print("BhoomiSatya — Government Portal Connectivity Test")
    print("=" * 80)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        headers={"User-Agent": "BhoomiSatya-PortalTest/0.1"},
    ) as client:
        results = await asyncio.gather(*(check_portal(client, name, url) for name, url in PORTALS))

    print(f"\n{'Portal':<40} {'URL':<45} {'Status':<8} {'Time':>8}")
    print("-" * 105)

    passed = 0
    for r in results:
        status_str = str(r["status"]) if r["status"] else "ERROR"
        indicator = "✅" if r["ok"] else "❌"
        print(f"{indicator} {r['name']:<38} {r['url']:<45} {status_str:<8} {r['time_ms']:>6}ms")
        if r.get("error"):
            print(f"   └─ {r['error']}")
        if r["ok"]:
            passed += 1

    print("-" * 105)
    print(f"Result: {passed}/{len(results)} portals reachable\n")


if __name__ == "__main__":
    asyncio.run(main())
