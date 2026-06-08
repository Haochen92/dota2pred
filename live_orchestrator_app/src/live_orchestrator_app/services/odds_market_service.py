from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.time_utils import (
    get_current_utc_iso_timestamp,
    to_utc_datetime_object,
    convert_redis_timestamp,
)
from dota_oracle_common.models.redis.schema import ConsumedEvent, OddsPayload
from dota_oracle_common.models.odds import OddsResultPayload, SnapshotKind, OddsSkipReason, PolymarketTeamMapTable
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.repositories.odds_repository import OddsRepository
from dota_oracle_pipeline.data_extraction.api_clients.polymarket_client import PolymarketClient

logger = get_logger(__name__)


class OddsMarketService:
    """Resolves a pending-odds event into a storable snapshot (or a recorded skip).

    This is the prefilter + match->market join: load team identity from the DB, build candidate
    names per team (the team's own Steam-side name, plus any polymarket_team_map alias for teams
    whose name differs across the two systems), then snapshot the order books. The map is an
    optional alias override, not a required gate -- most teams match directly on name. Network calls
    run OUTSIDE the DB session. Every event yields a terminal result (snapshot or no-market skip)
    except a transient resolution error inside the snapshot window, which is left pending to retry.
    """

    def __init__(
        self,
        db_session_factory: async_sessionmaker[AsyncSession],
        polymarket_client: PolymarketClient,
        snapshot_window_seconds: int,
    ):
        self.db_session_factory = db_session_factory
        self.polymarket_client = polymarket_client
        self.snapshot_window_seconds = snapshot_window_seconds

    async def resolve_snapshots(
        self, events: List[ConsumedEvent[OddsPayload]]
    ) -> List[ConsumedEvent[OddsResultPayload]]:
        if not events:
            return []

        match_ids = [event.match_id for event in events]

        # Load all DB context up front, then release the session before any network I/O.
        async with self.db_session_factory() as session:
            matches = await MatchRepository(session=session).get_match_details(input_id_list=match_ids)
            matches_by_id: Dict[int, MatchTable] = {m.match_id: m for m in matches}

            team_ids: List[int] = []
            for match in matches:
                team_ids.extend([match.radiant_team_id, match.dire_team_id])
            mappings = await OddsRepository(session=session).get_team_mappings(team_ids)
            mapping_by_team: Dict[int, PolymarketTeamMapTable] = {m.steam_team_id: m for m in mappings}

        now = get_current_utc_iso_timestamp()
        results: List[ConsumedEvent[OddsResultPayload]] = []
        for event in events:
            payload = await self._resolve_one(event, matches_by_id, mapping_by_team, now)
            if payload is not None:
                results.append(
                    ConsumedEvent[OddsResultPayload](event_id=event.event_id, match_id=event.match_id, payload=payload)
                )
        return results

    async def _resolve_one(
        self,
        event: ConsumedEvent[OddsPayload],
        matches_by_id: Dict[int, MatchTable],
        mapping_by_team: Dict[int, PolymarketTeamMapTable],
        now: datetime,
    ) -> Optional[OddsResultPayload]:
        """Resolve a single event. ``None`` means 'leave pending, retry next cycle'."""
        match_id = event.match_id
        match = matches_by_id.get(match_id)

        game_time_seconds: Optional[int] = None
        if match is not None and match.start_time is not None:
            start = to_utc_datetime_object(match.start_time)
            game_time_seconds = max(0, int((now - start).total_seconds()))

        if match is None:
            logger.warning(f"Odds: match {match_id} has no row in matches; recording no-market skip.")
            return self._skip(match_id, now, game_time_seconds, OddsSkipReason.NO_MARKET_FOUND)

        radiant_aliases = self._aliases(match.radiant_name, mapping_by_team.get(match.radiant_team_id))
        dire_aliases = self._aliases(match.dire_name, mapping_by_team.get(match.dire_team_id))
        if not radiant_aliases or not dire_aliases:
            # No usable team name from our feed AND no alias in the map -> nothing to match on.
            missing = [
                tid
                for tid, aliases in ((match.radiant_team_id, radiant_aliases), (match.dire_team_id, dire_aliases))
                if not aliases
            ]
            logger.warning(
                f"Odds: no team name or polymarket_team_map alias for team id(s) {missing} "
                f"(match {match_id}); recording no-market skip."
            )
            return self._skip(match_id, now, game_time_seconds, OddsSkipReason.NO_MARKET_FOUND)

        try:
            # Match Polymarket's outcome display names against each side's candidate names: the
            # team's own (Steam-side) name first, plus any team-map alias/slug for teams whose name
            # differs across the two systems.
            snapshot = await self.polymarket_client.get_market_snapshot(radiant_aliases, dire_aliases)
        except Exception as e:
            age_seconds = (now - convert_redis_timestamp(event.event_id)).total_seconds()
            if age_seconds < self.snapshot_window_seconds:
                logger.warning(
                    f"Odds: transient resolution error for match {match_id} "
                    f"(age {int(age_seconds)}s < {self.snapshot_window_seconds}s window); leaving pending. {e}"
                )
                return None
            logger.warning(
                f"Odds: resolution kept failing past the {self.snapshot_window_seconds}s window for "
                f"match {match_id}; recording no-market skip. {e}",
                exc_info=True,
            )
            return self._skip(match_id, now, game_time_seconds, OddsSkipReason.NO_MARKET_FOUND)

        if snapshot is None:
            return self._skip(match_id, now, game_time_seconds, OddsSkipReason.NO_MARKET_FOUND)

        return OddsResultPayload(
            match_id=match_id,
            snapshot_kind=SnapshotKind.ENTRY,
            captured_at=now,
            game_time_seconds=game_time_seconds,
            event_slug=snapshot.event_slug,
            market_slug=snapshot.market_slug,
            condition_id=snapshot.condition_id,
            token_id_a=snapshot.side_a.token_id,
            token_id_b=snapshot.side_b.token_id,
            a_best_bid=snapshot.side_a.best_bid,
            a_best_ask=snapshot.side_a.best_ask,
            a_liquidity=snapshot.side_a.liquidity,
            b_best_bid=snapshot.side_b.best_bid,
            b_best_ask=snapshot.side_b.best_ask,
            b_liquidity=snapshot.side_b.liquidity,
            raw=snapshot.raw,
        )

    @staticmethod
    def _aliases(steam_name: Optional[str], mapping: Optional[PolymarketTeamMapTable]) -> set:
        """Candidate names for matching a team to a Polymarket outcome: the team's own (Steam-side)
        name plus any team-map alias (canonical name + slug). The map is purely additive here."""
        keys = set()
        if steam_name:
            keys.add(steam_name)
        if mapping is not None:
            if mapping.canonical_name:
                keys.add(mapping.canonical_name)
            if mapping.polymarket_slug:
                keys.add(mapping.polymarket_slug)
        return keys

    @staticmethod
    def _skip(
        match_id: int, captured_at: datetime, game_time_seconds: Optional[int], reason: OddsSkipReason
    ) -> OddsResultPayload:
        return OddsResultPayload(
            match_id=match_id,
            snapshot_kind=SnapshotKind.ENTRY,
            captured_at=captured_at,
            game_time_seconds=game_time_seconds,
            skip_reason=reason,
        )
