from dota_oracle_common.repositories.history_repository import HistoryRepository
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.utils import get_logger
from dota_oracle_common.utils.time_utils import to_utc_datetime_object

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from dota_oracle_common.models.match import MatchTable

logger = get_logger(__name__)


class HistoryUpdateService:
    async def update_histories(self, db_session_factory: async_sessionmaker[AsyncSession], match_id: int) -> None:
        """
        Updates all history records for a single match within one atomic transaction.
        If any single update fails, all previous updates for this match are rolled back.
        """
        logger.info(f"Starting atomic history update for match {match_id}")

        async with db_session_factory() as session:
            async with session.begin():
                try:
                    # Create the repository once with the session for this transaction
                    history_repository = HistoryRepository(session=session)

                    # Step 1: Fetch the necessary data using the current session.
                    match_details = await self._get_completed_match_details(match_id, session)
                    match_outcome = match_details.outcome
                    if not match_outcome:
                        raise ValueError(f"Match outcome for {match_id} not found.")

                    start_time_obj = to_utc_datetime_object(match_details.start_time)

                    # Step 2: Update team histories SEQUENTIALLY
                    await history_repository.add_team_match_outcome(
                        team_name=match_details.radiant_name,
                        match_id=match_id,
                        win=match_outcome.radiant_win,
                        match_start_time=start_time_obj,
                    )
                    await history_repository.add_team_match_outcome(
                        team_name=match_details.dire_name,
                        match_id=match_id,
                        win=not match_outcome.radiant_win,
                        match_start_time=start_time_obj,
                    )
                    await history_repository.add_team_matchup_outcome(
                        team_one=match_details.radiant_name,
                        team_two=match_details.dire_name,
                        match_id=match_id,
                        win=match_outcome.radiant_win,
                        match_start_time=start_time_obj,
                    )

                    # Step 3: Update player-hero histories SEQUENTIALLY
                    for i in list(range(0, 5)) + list(range(128, 133)):
                        account_id = getattr(match_details, f"slot_{i}_account_id")
                        hero_id = getattr(match_details, f"slot_{i}_hero_id")
                        win = match_outcome.radiant_win if i < 5 else not match_outcome.radiant_win

                        await history_repository.add_player_hero_match_outcome(
                            account_id=account_id,
                            hero_id=hero_id,
                            match_id=match_id,
                            win=win,
                            match_start_time=start_time_obj,
                        )

                    # If we reach this point, all operations were successful.
                    logger.info(f"All 13 history updates for match {match_id} are ready to be committed.")

                except Exception as e:
                    logger.error(
                        f"History update transaction failed for match {match_id}. "
                        f"All changes for this match will be rolled back. Error: {e}",
                        exc_info=True,
                    )
                    raise

        logger.info(f"Successfully committed all history updates for match {match_id}.")

    async def _get_completed_match_details(self, match_id: int, session: AsyncSession) -> MatchTable:
        """Fetches match details using a provided, active session."""
        match_repository = MatchRepository(session=session)
        res = await match_repository.get_match_details(input_id_list=[match_id], relationship_fields=["outcome"])

        if not res:
            raise ValueError(f"Match {match_id} cannot be found in database.")

        return res[0]
