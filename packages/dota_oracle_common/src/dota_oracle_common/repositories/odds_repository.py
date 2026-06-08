from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select, col

from ..models.odds import MatchOddsSnapshotTable, PolymarketTeamMapTable, MatchPaperBetTable
from ..utils.set_logging import get_logger
from .base_repository import BaseRepository

logger = get_logger(__name__)


class OddsRepository(BaseRepository):
    """Repository for Polymarket odds snapshots and the team-id -> slug bridge."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def upsert_odds_snapshots(self, instances: List[MatchOddsSnapshotTable]) -> None:
        """Upsert odds snapshots using INSERT ... ON CONFLICT DO UPDATE on (match_id, snapshot_kind).

        Idempotent re-capture: a re-processed match overwrites its prior snapshot of the same kind.
        """
        if not instances:
            logger.debug("No MatchOddsSnapshotTable instances provided for upsert_odds_snapshots.")
            return
        try:
            await self._upsert_data(model_class=MatchOddsSnapshotTable, instances=instances)
        except Exception as e:
            logger.error(f"Error encountered when upserting odds snapshots: {e}", exc_info=True)
            raise

    async def upsert_paper_bets(self, instances: List[MatchPaperBetTable]) -> None:
        """Upsert offline replay results on (match_id, predictor_name). Last replay wins."""
        if not instances:
            logger.debug("No MatchPaperBetTable instances provided for upsert_paper_bets.")
            return
        try:
            await self._upsert_data(model_class=MatchPaperBetTable, instances=instances)
        except Exception as e:
            logger.error(f"Error encountered when upserting paper bets: {e}", exc_info=True)
            raise

    async def get_entry_snapshots_with_prices(self) -> List[MatchOddsSnapshotTable]:
        """All ENTRY snapshots that actually captured a market (skip_reason IS NULL), oldest first.

        The replay iterates these in capture order so fractional-Kelly can compound a running
        bankroll the way the live sequence would have.
        """
        try:
            stmt = (
                select(MatchOddsSnapshotTable)
                .where(
                    col(MatchOddsSnapshotTable.snapshot_kind) == "entry",
                    col(MatchOddsSnapshotTable.skip_reason).is_(None),
                )
                .order_by(col(MatchOddsSnapshotTable.captured_at).asc())
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching entry snapshots: {e}", exc_info=True)
            raise

    async def upsert_team_mappings(self, instances: List[PolymarketTeamMapTable]) -> None:
        """Upsert team-map rows using INSERT ... ON CONFLICT DO UPDATE on steam_team_id."""
        if not instances:
            logger.debug("No PolymarketTeamMapTable instances provided for upsert_team_mappings.")
            return
        try:
            await self._upsert_data(model_class=PolymarketTeamMapTable, instances=instances)
        except Exception as e:
            logger.error(f"Error encountered when upserting team mappings: {e}", exc_info=True)
            raise

    async def get_team_mappings(self, steam_team_ids: List[int]) -> List[PolymarketTeamMapTable]:
        """Fetch the Polymarket slug mappings for the given Steam team ids (those that exist)."""
        if not steam_team_ids:
            return []
        try:
            stmt = select(PolymarketTeamMapTable).where(
                PolymarketTeamMapTable.steam_team_id.in_(steam_team_ids)  # type: ignore[attr-defined]
            )
            result = await self.session.execute(stmt)
            mappings: List[PolymarketTeamMapTable] = list(result.scalars().all())
            logger.debug(f"Resolved {len(mappings)}/{len(steam_team_ids)} team mappings from polymarket_team_map")
            return mappings
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching team mappings for {steam_team_ids}: {e}", exc_info=True)
            raise
