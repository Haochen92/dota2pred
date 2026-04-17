from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.models.match.schema import CompletedMatchAPIPayload
from dota_oracle_common.models.pagination import PaginationFilters, PaginatedMatchResponse
from dota_oracle_common.repositories.patch_repository import PatchRepository
from dota_oracle_common.utils import load_workspace_env, get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import selectinload

from typing import Dict

logger = get_logger(__name__)

load_workspace_env()


class MatchPaginationService:
    def __init__(
        self,
        db_session: AsyncSession,
        patch_repository: PatchRepository,
        hero_map: Dict[int, str],
    ):
        self.session = db_session
        self.hero_map = hero_map
        self.patch_repository = patch_repository

    async def get_paginated_matches(
        self,
        filters: PaginationFilters,
    ) -> PaginatedMatchResponse:
        """Fetches paginated matches, orchestrating name/number resolutions."""
        offset = filters.offset if filters.offset is not None else 0
        limit = filters.limit if filters.limit is not None else 0

        # Build base query for completed matches with outcomes and predictions
        base_query = (
            select(MatchTable)
            .join(MatchTable.outcome, isouter=False)  # Only matches with outcomes (completed matches) # type: ignore
            .join(MatchTable.league_data, isouter=True)  # type: ignore
            .options(
                selectinload(MatchTable.outcome),  # type: ignore
                selectinload(MatchTable.predictions),  # type: ignore
                selectinload(MatchTable.league_data),  # type: ignore
            )
        )

        # Resolve and apply filters
        await self._resolve_patch_filters(filters)
        base_query = self._apply_filters(base_query, filters)

        # Order by match_id descending (latest first)
        base_query = base_query.order_by(desc(MatchTable.match_id))  # type: ignore

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_count_result = await self.session.execute(count_query)
        total_count = total_count_result.scalar_one_or_none() or 0

        completed_matches = []

        # Early return if no data is requested or no matches found
        if not limit or not total_count:
            return PaginatedMatchResponse(
                matches=completed_matches,
                total_count=total_count,
                total_pages=0,
            )

        # Get paginated results
        paginated_query = base_query.offset(offset).limit(limit)
        result = await self.session.execute(paginated_query)
        matches = result.scalars().all()

        total_pages = (total_count + limit - 1) // limit

        logger.info(f"Retrieved {len(matches)} matches, total_pages = {total_pages}")

        for match in matches:
            predicted_outcome = match.predictions[0].prediction if match.predictions else None
            # Construct data dict
            payload_data = {
                **match.model_dump(),
                "radiant_win": match.outcome.radiant_win,
                "predicted_outcome": predicted_outcome,
                "league_data": match.league_data.model_dump() if match.league_data else None,
            }

            completed_match = CompletedMatchAPIPayload.model_validate(payload_data)
            completed_matches.append(completed_match)

        return PaginatedMatchResponse(
            matches=completed_matches,
            total_count=total_count,
            total_pages=total_pages,
        )

    async def _resolve_patch_filters(self, filters: PaginationFilters):
        """Translates user-friendly names/numbers into database-friendly IDs and date ranges."""

        # Resolve Patch Number to Date Range
        if filters.patch_number:
            patch = await self.patch_repository.get_patch_by_number(filters.patch_number)
            if not patch:
                raise ValueError(f"Patch '{filters.patch_number}' not found.")

            # Use datetime objects directly for filtering
            filters.patch_start_time = patch.start_time
            if patch.end_time:
                filters.patch_end_time = patch.end_time

    def _apply_filters(self, query, filters: PaginationFilters):
        """Apply filters to the base query"""
        conditions = []

        # Filter by specific match_id
        if filters.match_id:
            conditions.append(MatchTable.match_id == filters.match_id)

        # Filter by team name (radiant or dire)
        if filters.team_name:
            team_name_filter = or_(
                MatchTable.radiant_name.ilike(f"%{filters.team_name}%"),  # type: ignore[attr-defined]
                MatchTable.dire_name.ilike(f"%{filters.team_name}%"),  # type: ignore[attr-defined]
            )
            conditions.append(team_name_filter)

        # Filter by team IDs (radiant or dire)
        if filters.team_ids:
            team_id_filter = or_(
                MatchTable.radiant_team_id.in_(filters.team_ids),  # type: ignore[attr-defined]
                MatchTable.dire_team_id.in_(filters.team_ids),  # type: ignore[attr-defined]
            )
            conditions.append(team_id_filter)

        # Filter by hero IDs (any of the 10 slots)
        if filters.hero_ids:
            hero_slots = [
                MatchTable.slot_0_hero_id,
                MatchTable.slot_1_hero_id,
                MatchTable.slot_2_hero_id,
                MatchTable.slot_3_hero_id,
                MatchTable.slot_4_hero_id,
                MatchTable.slot_128_hero_id,
                MatchTable.slot_129_hero_id,
                MatchTable.slot_130_hero_id,
                MatchTable.slot_131_hero_id,
                MatchTable.slot_132_hero_id,
            ]
            conditions.append(or_(*[slot.in_(filters.hero_ids) for slot in hero_slots]))  # type: ignore[attr-defined]

        # Filter by patch time range
        if filters.patch_start_time is not None:
            conditions.append(MatchTable.start_time >= filters.patch_start_time)
        if filters.patch_end_time is not None:
            conditions.append(MatchTable.start_time < filters.patch_end_time)

        # Filter by league ID (exact match)
        if filters.league_id is not None:
            conditions.append(MatchTable.leagueid == filters.league_id)

        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))

        return query
