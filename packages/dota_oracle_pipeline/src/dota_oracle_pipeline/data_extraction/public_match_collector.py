import asyncio
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import async_sessionmaker

from dota_oracle_common.utils import get_logger
from dota_oracle_common.repositories.public_match_repository import PublicMatchRepository
from dota_oracle_common.models.match import PublicMatchTable

from .public_matches_stream import stream_public_matches
from ..data_transformation.public_matches_mapper import to_public_match_table


logger = get_logger(__name__)


class PublicMatchCollector:
    """
    Collect public matches into the database for a given match_id window.

    - Streams via OpenDota publicMatches API (descending by match_id).
    - Inserts in batches with ON CONFLICT DO NOTHING and counts net-new inserts.
    - Supports multi-pass by restarting from the top boundary to recover from transient gaps.
    - Optional hop on no-progress to start further back in time.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker,
        min_rank: int,
        max_rank: int,
        insert_batch_size: int = 500,
        error_hop_match_ids: int = 50000,
        hop_max: int = 40000,
        max_passes: int = 3,
        hop_on_no_progress: int = 0,
        backoff_seconds_between_passes: int = 0,
    ) -> None:
        self._session_factory = session_factory
        self._min_rank = min_rank
        self._max_rank = max_rank
        self._insert_batch_size = insert_batch_size
        self._error_hop_match_ids = error_hop_match_ids
        self._hop_max = hop_max
        self._max_passes = max_passes
        self._hop_on_no_progress = hop_on_no_progress
        self._backoff = backoff_seconds_between_passes

        # session handle set in collect_range for use by helpers
        self.session = None

    async def _process_batch(
        self,
        repo: PublicMatchRepository,
        batch: List[PublicMatchTable],
        current_pass: int,
        total_new: int,
        target_match_count: int,
    ) -> int:
        """Insert a batch, commit, log, and return number of newly inserted rows."""
        if not batch:
            return 0

        ids = await repo.insert_public_matches_returning_ids(batch)
        # commit via the session attached during collect_range
        await self.session.commit()  # type: ignore
        newly_inserted = len(ids)

        logger.info(
            f"[pass {current_pass}] Inserted {newly_inserted} new matches. "
            f"Total: {total_new + newly_inserted}/{target_match_count}."
        )
        return newly_inserted

    def _determine_next_action(
        self,
        pass_new: int,
        current_cursor: int,
        start_match_id: int,
        end_match_id: int,
    ) -> Dict[str, Any]:
        """Decide whether to stop, hop the cursor downward, or restart from the top."""
        if pass_new > 0:
            logger.info(f"Progress made ({pass_new} new matches). Resetting cursor to {start_match_id} for next pass.")
            return {"stop": False, "next_cursor": start_match_id}

        if self._hop_on_no_progress > 0:
            new_cursor = max(end_match_id, current_cursor - self._hop_on_no_progress)
            if new_cursor == current_cursor:
                logger.info("No progress and cannot hop further. Stopping collection.")
                return {"stop": True, "next_cursor": current_cursor}
            logger.info(f"No progress. Hopping start cursor from {current_cursor} to {new_cursor}.")
            return {"stop": False, "next_cursor": new_cursor}

        logger.info("No progress made in the last pass. Stopping collection.")
        return {"stop": True, "next_cursor": current_cursor}

    async def collect_range(
        self,
        *,
        start_match_id: int,
        end_match_id: int,
        target_match_count: int,
    ) -> Dict[str, Any]:
        """
        Run up to `max_passes` descending scans from `start_match_id` down to `end_match_id` until
        we insert at least `target_match_count` unique matches, or no further progress is made.
        """
        total_new = 0
        passes = 0
        start_cursor = start_match_id

        async with self._session_factory() as session:
            self.session = session
            repo = PublicMatchRepository(session)

            while passes < self._max_passes and total_new < target_match_count:
                passes += 1
                pass_new = 0
                batch: List[PublicMatchTable] = []

                async for match in stream_public_matches(
                    start_less_than_match_id=start_cursor,
                    min_rank=self._min_rank,
                    max_rank=self._max_rank,
                    error_hop_match_ids=self._error_hop_match_ids,
                    hop_max=self._hop_max,
                    stop_at_match_id=end_match_id,
                ):
                    if match.match_id < end_match_id:
                        logger.info(f"End boundary reached at match {match.match_id}. Finishing pass {passes}.")
                        break

                    try:
                        batch.append(to_public_match_table(match))
                    except Exception as e:
                        logger.warning(f"Skipping malformed match {match.match_id}: {e}")
                        continue

                    if len(batch) >= self._insert_batch_size:
                        newly_inserted = await self._process_batch(repo, batch, passes, total_new, target_match_count)
                        pass_new += newly_inserted
                        total_new += newly_inserted
                        batch.clear()

                        if total_new >= target_match_count:
                            break

                # Final batch for the pass
                newly_inserted = await self._process_batch(repo, batch, passes, total_new, target_match_count)
                pass_new += newly_inserted
                total_new += newly_inserted

                if total_new >= target_match_count:
                    break

                next_action = self._determine_next_action(pass_new, start_cursor, start_match_id, end_match_id)
                if next_action["stop"]:
                    break

                start_cursor = next_action["next_cursor"]
                if self._backoff > 0 and pass_new > 0:
                    await asyncio.sleep(self._backoff)

        logger.info(f"Collection finished. Total new: {total_new}. Target: {target_match_count}. Passes: {passes}.")
        return {
            "total_new": total_new,
            "passes": passes,
            "completed": total_new >= target_match_count,
        }
