from fastapi import HTTPException, status
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
        page = filters.page
        page_size = filters.page_size

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:  # Cap at 100 for performance
            page_size = 20

        offset = (page - 1) * page_size

        # Build base query for completed matches with outcomes and predictions
        base_query = (
            select(MatchTable)
            .join(MatchTable.outcome, isouter=False)  # Only matches with outcomes (completed matches) # type: ignore
            .options(
                selectinload(MatchTable.outcome),  # type: ignore
                selectinload(MatchTable.predictions),  # type: ignore
            )
        )

        # Resolve and apply filters
        await self._resolve_and_update_filters(filters)
        base_query = self._apply_filters(base_query, filters)

        # Order by match_id descending (latest first)
        base_query = base_query.order_by(desc(MatchTable.match_id))  # type: ignore

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_count_result = await self.session.execute(count_query)
        total_count = total_count_result.scalar_one_or_none() or 0

        # Get paginated results
        paginated_query = base_query.offset(offset).limit(page_size)
        result = await self.session.execute(paginated_query)
        matches = result.scalars().all()

        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
        has_next = page < total_pages
        has_previous = page > 1

        logger.info(f"Retrieved {len(matches)} matches for page {page}/{total_pages} (Total: {total_count})")

        # Convert MatchTable instances to CompletedMatchAPIPayload
        completed_matches = []
        for match in matches:
            # Get the first prediction from the predictions list
            predicted_outcome = None
            if match.predictions and len(match.predictions) > 0:
                predicted_outcome = match.predictions[0].prediction
            else:
                logger.warning(f"No prediction found for match {match.match_id}")
                continue  # Skip matches without predictions

            # Convert match to dict and add predicted_outcome and radiant_win
            match_dict = match.model_dump()
            match_dict["predicted_outcome"] = predicted_outcome
            match_dict["radiant_win"] = match.outcome.radiant_win

            # Create CompletedMatchAPIPayload using model_validate
            completed_match = CompletedMatchAPIPayload.model_validate(match_dict)
            completed_matches.append(completed_match)

        return PaginatedMatchResponse(
            matches=completed_matches,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        )

    async def _resolve_and_update_filters(self, filters: PaginationFilters):
        """Translates user-friendly names/numbers into database-friendly IDs and date ranges."""
        # Resolve Hero Names to IDs
        if filters.hero_names and not filters.hero_ids:
            hero_map = self.hero_map
            hero_name_to_id = {name.lower(): hero_id for hero_id, name in hero_map.items()}

            hero_ids = []
            missing_names = []

            for hero_name in filters.hero_names:
                hero_id = hero_name_to_id.get(hero_name.lower())
                if hero_id:
                    hero_ids.append(hero_id)
                else:
                    missing_names.append(hero_name)

            if missing_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not find the following heroes: {', '.join(missing_names)}.",
                )
            filters.hero_ids = hero_ids

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
                MatchTable.radiant_name.ilike(f"%{filters.team_name}%"),
                MatchTable.dire_name.ilike(f"%{filters.team_name}%"),
            )
            conditions.append(team_name_filter)

        # Filter by team IDs (radiant or dire)
        if filters.team_ids:
            team_id_filter = or_(
                MatchTable.radiant_team_id.in_(filters.team_ids), MatchTable.dire_team_id.in_(filters.team_ids)
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
            conditions.append(or_(*[slot.in_(filters.hero_ids) for slot in hero_slots]))

        # Filter by patch time range
        if filters.patch_start_time is not None:
            conditions.append(MatchTable.start_time >= filters.patch_start_time)
        if filters.patch_end_time is not None:
            conditions.append(MatchTable.start_time < filters.patch_end_time)

        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))

        return query
