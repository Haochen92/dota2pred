"""Seed / maintain the polymarket_team_map ALIAS table (steam_team_id -> Polymarket slug).

The resolver matches a match's own team names directly against Polymarket's market outcomes, so this
table is an OPTIONAL override -- you only need an entry for a team whose Steam-side name doesn't
string-match its Polymarket display name (the resolver logs a WARN naming those). Most teams need no
entry at all.

Two subcommands:

    propose  Harvest the team display names from Polymarket's open Dota game markets, match each to
             an OpenDota team (by normalized name) to propose a steam_team_id, and write a REVIEWABLE
             JSON seed file. Everything is written verified=false; entries with no confident OpenDota
             match are flagged needs_review. No DB writes.

    load     Read the (human-reviewed) seed file and upsert it into polymarket_team_map. Use
             --only-verified to load only rows a human has marked "verified": true.

Workflow: run `propose` -> eyeball/fix the JSON (set steam_team_id where missing, flip verified to
true once the slug is confirmed) -> run `load --only-verified`. The odds resolver logs a WARN for
any team id it can't map, which tells you what to add next. See
docs/2026-06-08-polymarket-odds-capture.md.
"""

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from dota_oracle_common.constants.endpoint_configs import service_url
from dota_oracle_common.models.odds import PolymarketTeamMapTable
from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.repositories.odds_repository import OddsRepository
from dota_oracle_common.utils import get_logger
from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp
from dota_oracle_pipeline.data_extraction.api_clients.opendota_api import fetch_opendota
from dota_oracle_pipeline.data_extraction.api_clients.polymarket_client import PolymarketClient

logger = get_logger(__name__)

SEED_PATH = Path(__file__).with_name("polymarket_team_map_seed.json")


def _norm(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower().replace("-", " ").replace("_", " "))


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


async def _harvest_polymarket_team_names() -> List[str]:
    """Unique team display names appearing in Polymarket's open Dota Game-1 markets."""
    async with httpx.AsyncClient(timeout=30.0) as http:
        client = PolymarketClient(
            http_client=http,
            gamma_url=service_url.BASE_GAMMA_URL,
            clob_url=service_url.BASE_CLOB_URL,
            tag_slug=service_url.ODDS_DOTA_TAG_SLUG,
        )
        events = await client._discover_events()
        names = set()
        for _event_slug, market in client._candidate_game_markets(events):
            for outcome in client._parse_outcomes(market):
                cleaned = outcome.strip()
                if cleaned:
                    names.add(cleaned)
    return sorted(names)


async def cmd_propose() -> None:
    pm_names = await _harvest_polymarket_team_names()
    logger.info(f"Harvested {len(pm_names)} Polymarket team names from open Dota game markets.")

    opendota_teams = await fetch_opendota("teams")
    by_norm: Dict[str, dict] = {}
    for team in opendota_teams:
        name = team.get("name")
        if name:
            by_norm.setdefault(_norm(name), team)

    records = []
    for name in pm_names:
        match = by_norm.get(_norm(name))
        records.append(
            {
                "canonical_name": name,
                "polymarket_slug": _slugify(name),
                "steam_team_id": match.get("team_id") if match else None,
                "matched_opendota_name": match.get("name") if match else None,
                # Written false: a human confirms the slug + steam_team_id before load --only-verified.
                "verified": False,
                "needs_review": match is None,
            }
        )

    SEED_PATH.write_text(json.dumps(records, indent=2))
    unmatched = sum(1 for r in records if r["steam_team_id"] is None)
    logger.info(
        f"Wrote {len(records)} proposed mappings to {SEED_PATH.name} "
        f"({unmatched} need a manual steam_team_id). Review, set verified=true, then run `load`."
    )


async def cmd_load(only_verified: bool) -> None:
    if not SEED_PATH.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_PATH}. Run `propose` first.")

    records = json.loads(SEED_PATH.read_text())
    now = get_current_utc_iso_timestamp()
    rows: List[PolymarketTeamMapTable] = []
    skipped = 0
    for record in records:
        if record.get("steam_team_id") is None:
            skipped += 1
            continue
        if only_verified and not record.get("verified"):
            skipped += 1
            continue
        rows.append(
            PolymarketTeamMapTable(
                steam_team_id=record["steam_team_id"],
                polymarket_slug=record["polymarket_slug"],
                canonical_name=record["canonical_name"],
                verified=bool(record.get("verified")),
                updated_at=now,
            )
        )

    if not rows:
        logger.warning(f"No loadable rows (skipped {skipped}). Set steam_team_id/verified in {SEED_PATH.name}.")
        return

    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        async with session.begin():
            await OddsRepository(session=session).upsert_team_mappings(rows)
    logger.info(f"Upserted {len(rows)} team mappings into polymarket_team_map (skipped {skipped}).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed/maintain the polymarket_team_map bridge.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("propose", help="Harvest Polymarket teams + propose mappings to a reviewable JSON.")
    load_parser = sub.add_parser("load", help="Upsert the reviewed seed JSON into the DB.")
    load_parser.add_argument("--only-verified", action="store_true", help="Load only rows marked verified=true.")

    args = parser.parse_args()
    if args.command == "propose":
        asyncio.run(cmd_propose())
    elif args.command == "load":
        asyncio.run(cmd_load(only_verified=args.only_verified))


if __name__ == "__main__":
    main()
