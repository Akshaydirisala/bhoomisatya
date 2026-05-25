#!/usr/bin/env python3
"""Seed district/mandal/village hierarchy into the database.

Reads from data/districts_telangana.json and data/districts_ap.json and upserts
records into the districts, mandals, and villages tables.

Usage:
    python -m scripts.seed_districts
"""

import asyncio
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DISTRICT_FILES = {
    "telangana": DATA_DIR / "districts_telangana.json",
    "andhra_pradesh": DATA_DIR / "districts_ap.json",
}


async def seed_state(state: str, filepath: Path):
    """Load districts for a single state."""
    with open(filepath) as f:
        districts = json.load(f)

    total_mandals = sum(len(d["mandals"]) for d in districts)
    total_villages = sum(len(m["villages"]) for d in districts for m in d["mandals"])

    print(f"  State: {state}")
    print(f"    Districts: {len(districts)}")
    print(f"    Mandals:   {total_mandals}")
    print(f"    Villages:  {total_villages}")

    # TODO: implement full seeding into PostgreSQL
    # Steps:
    #   1. Connect to DB via src.database
    #   2. For each district -> upsert into districts table
    #   3. For each mandal  -> upsert into mandals table (FK to district)
    #   4. For each village -> upsert into villages table (FK to mandal)
    #   5. Commit transaction
    print("    ⚠️  TODO: implement full seeding — currently prints stats only\n")


async def main():
    print("=" * 60)
    print("BhoomiSatya — District Hierarchy Seeder")
    print("=" * 60 + "\n")

    for state, filepath in DISTRICT_FILES.items():
        if not filepath.exists():
            print(f"  ⚠️  Missing file: {filepath}")
            continue
        await seed_state(state, filepath)

    print("Done. Full database seeding is not yet implemented.")
    print("Next step: connect to src.database and upsert records.")


if __name__ == "__main__":
    asyncio.run(main())
