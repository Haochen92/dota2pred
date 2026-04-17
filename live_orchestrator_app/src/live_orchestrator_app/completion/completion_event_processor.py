from dota_oracle_common.utils.set_logging import get_logger
from ..services.history_update_service import HistoryUpdateService
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.models.match import MatchOutcomeTable
from dota_oracle_common.models.redis.schema import ConsumedEvent, CompletedMatchPayload
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession


logger = get_logger(__name__)


class CompletionEventProcessor:
    def __init__(
        self, history_update_service: HistoryUpdateService, db_session_factory: async_sessionmaker[AsyncSession]
    ):
        self.history_updater = history_update_service
        self.db_session_factory = db_session_factory

    async def process_events(self, work_item: ConsumedEvent[CompletedMatchPayload]) -> bool:
        try:
            match_id = work_item.match_id
            match_outcome = work_item.payload.match_outcome

            # store match outcome
            await self._update_match_outcome(match_id=match_id, match_outcome=match_outcome)

            # update related match histories
            await self.history_updater.update_all_histories_for_match(self.db_session_factory, match_id)

            logger.debug(f"Successfully stored match outcome and match histories for match_id: {match_id}")

            return True
        except Exception as e:
            raise e

    async def _update_match_outcome(self, match_id: int, match_outcome: bool) -> None:
        async with self.db_session_factory() as session:
            async with session.begin():
                match_repository = MatchRepository(session=session)
                try:
                    outcome_instance = MatchOutcomeTable(match_id=match_id, radiant_win=match_outcome)
                    await match_repository.insert_match_outcome([outcome_instance])
                    logger.debug(f"Successfully updated match_outcome for match: {match_id}")
                except Exception as e:
                    logger.error(f"Failed to update match outcome, {e}", exc_info=True)
                    raise e
