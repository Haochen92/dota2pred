from dota_oracle.utils.set_logging import get_logger
from ..services.history_update_service import HistoryUpdateService
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.models.match import MatchOutcomeTable
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from dota_oracle.models.pipeline import CompletionWorkItem

logger = get_logger(__name__)
class CompletionEventProcessor:
    def __init__(
        self, 
        history_update_service: HistoryUpdateService,
        db_engine: AsyncEngine
    ):
        self.history_updater = history_update_service
        self.engine = db_engine
    
    async def process_events(self, work_item: CompletionWorkItem):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                try:
                    event_data = work_item.event_data
                    match_outcome = work_item.outcome
                    # create repository
                    match_repository = MatchRepository(session=session)
                    
                    # store match outcome
                    await self._update_match_outcome(
                        match_repository=match_repository, 
                        match_id=event_data.match_id, 
                        match_outcome=match_outcome
                    )
                    
                    # update related match histories
                    await self.history_updater.update_histories(session, event_data.match_id)
                except Exception as e:
                    raise e
            
    async def _update_match_outcome(self, match_repository: MatchRepository, match_id: int, match_outcome: bool):
        try:
            outcome_instance = MatchOutcomeTable(match_id=match_id, radiant_win=match_outcome)
            await match_repository.insert_match_outcome([outcome_instance])
        except Exception as e:
            logger.error(f"Failed to update match outcome, {e}", exc_info=True)
            raise e