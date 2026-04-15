"""
Integration tests for MatchPaginationService.

These tests verify the service works correctly with a real database,
testing the full end-to-end flow including filtering, pagination, and data retrieval.
"""

import pytest
from datetime import datetime, timezone

from api_service.matches.match_pagination_service import MatchPaginationService
from dota_oracle_common.models.pagination import PaginationFilters

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestMatchPaginationServiceIntegration:
    """Integration tests for MatchPaginationService with real database."""

    async def test_get_paginated_matches_happy_path(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test successful retrieval of paginated matches with default filters."""
        # ARRANGE
        filters = PaginationFilters(offset=0, limit=10)

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        assert result is not None
        assert len(result.matches) == 10  # First page of results
        assert result.total_count == 15  # Only completed matches (with outcomes)
        assert result.total_pages == 2  # 15 total / 10 per page = 2 pages

        # Verify all returned matches have outcomes and predictions
        for match in result.matches:
            assert hasattr(match, "radiant_win")  # Has outcome data
            assert hasattr(match, "predicted_outcome")  # Has prediction data

    async def test_get_paginated_matches_second_page(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test retrieval of second page."""
        # ARRANGE
        filters = PaginationFilters(offset=10, limit=10)

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        assert result is not None
        assert len(result.matches) == 5  # Remaining matches on second page
        assert result.total_count == 15
        assert result.total_pages == 2

    async def test_get_paginated_matches_filter_by_match_id(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test filtering by specific match ID."""
        # ARRANGE
        test_data = seed_pagination_test_data
        target_match_id = test_data["completed_match_ids"][0]  # Use a completed match
        filters = PaginationFilters(offset=0, limit=10, match_id=target_match_id)

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        assert result is not None
        assert len(result.matches) == 1
        assert result.matches[0].match_id == target_match_id
        assert result.total_count == 1

    async def test_get_paginated_matches_filter_by_hero_id(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test filtering by hero IDs using the current query model."""
        # ARRANGE
        filters = PaginationFilters(offset=0, limit=20, hero_ids=[1])

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        assert result.total_count == 10
        assert len(result.matches) == 10
        assert all(match.slot_0_hero_id == 1 for match in result.matches)

    async def test_resolve_and_update_filters_patch_number(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test patch number resolution to date range."""
        # ARRANGE
        filters = PaginationFilters(offset=0, limit=10, patch_number="7.35")

        # ACT
        await integration_test_match_pagination_service._resolve_patch_filters(filters)

        # ASSERT
        assert filters.patch_start_time == datetime(2023, 6, 1, tzinfo=timezone.utc)
        assert filters.patch_end_time == datetime(2024, 1, 1, tzinfo=timezone.utc)

    async def test_resolve_and_update_filters_unknown_patch(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test patch number resolution with unknown patch raises ValueError."""
        # ARRANGE
        filters = PaginationFilters(offset=0, limit=10, patch_number="7.99")  # Non-existent patch

        # ACT & ASSERT
        with pytest.raises(ValueError) as exc_info:
            await integration_test_match_pagination_service._resolve_patch_filters(filters)

        assert "Patch '7.99' not found" in str(exc_info.value)

    async def test_get_paginated_matches_with_patch_filter(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test pagination with patch-based date filtering."""
        # ARRANGE
        filters = PaginationFilters(offset=0, limit=20, patch_number="7.35")  # Large page size to get all results

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        assert result is not None
        # Should return matches from 7.35 patch period (first 10 matches in our test data)
        assert len(result.matches) == 10  # Matches from 7.35 period with outcomes
        for match in result.matches:
            # Verify matches are within the patch date range
            match_time = match.start_time
            assert match_time >= datetime(2023, 6, 1, tzinfo=timezone.utc)
            assert match_time < datetime(2024, 1, 1, tzinfo=timezone.utc)

    async def test_get_paginated_matches_edge_case_large_page_number(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test pagination handles large page numbers gracefully."""
        # ARRANGE
        filters = PaginationFilters(offset=9990, limit=10)  # Very large offset

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        # Should return empty results but valid response structure
        assert result is not None
        assert len(result.matches) == 0
        assert result.total_count == 15  # Total still correct

    async def test_get_paginated_matches_edge_case_max_page_size(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test pagination with maximum allowed page size."""
        # ARRANGE
        filters = PaginationFilters(offset=0, limit=50)  # Current maximum allowed size

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        # Should return all results in one page
        assert len(result.matches) == 15  # All completed matches
        assert result.total_pages == 1

    async def test_get_paginated_matches_no_results(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test pagination when no matches are found."""
        # ARRANGE
        filters = PaginationFilters(offset=0, limit=10, match_id=999999)  # Non-existent match ID

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        assert result is not None
        assert len(result.matches) == 0
        assert result.total_count == 0
        assert result.total_pages == 0
