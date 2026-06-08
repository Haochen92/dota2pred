from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.repositories.odds_repository import OddsRepository
from dota_oracle_common.models.redis.schema import ConsumedEvent
from dota_oracle_common.models.odds import OddsResultPayload, MatchOddsSnapshotTable

logger = get_logger(__name__)


class OddsEventProcessor:
    """Persists a resolved odds work item as a MatchOddsSnapshotTable row (snapshot or skip)."""

    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession]):
        self.db_session_factory = db_session_factory

    async def process_event(self, event: ConsumedEvent[OddsResultPayload]) -> bool:
        payload = event.payload
        snapshot = MatchOddsSnapshotTable(
            match_id=payload.match_id,
            snapshot_kind=payload.snapshot_kind.value,
            captured_at=payload.captured_at,
            game_time_seconds=payload.game_time_seconds,
            provider=payload.provider,
            event_slug=payload.event_slug,
            market_slug=payload.market_slug,
            condition_id=payload.condition_id,
            token_id_a=payload.token_id_a,
            token_id_b=payload.token_id_b,
            a_best_bid=payload.a_best_bid,
            a_best_ask=payload.a_best_ask,
            a_liquidity=payload.a_liquidity,
            b_best_bid=payload.b_best_bid,
            b_best_ask=payload.b_best_ask,
            b_liquidity=payload.b_liquidity,
            skip_reason=payload.skip_reason.value if payload.skip_reason else None,
            raw=payload.raw,
        )

        async with self.db_session_factory() as session:
            async with session.begin():
                await OddsRepository(session=session).upsert_odds_snapshots([snapshot])

        logger.debug(
            f"Stored odds snapshot for match {payload.match_id} "
            f"({'skip:' + payload.skip_reason.value if payload.skip_reason else 'captured'})"
        )
        return True
