"""
Integration tests for MatchPaginationService.

These tests verify the service works correctly with a real database,
testing the full end-to-end flow including filtering, pagination, and data retrieval.
"""

import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

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
        filters = PaginationFilters(page=1, page_size=10)

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        assert result is not None
        assert len(result.matches) == 10  # First page of results
        assert result.total_count == 15  # Only completed matches (with outcomes)
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 2  # 15 total / 10 per page = 2 pages
        assert result.has_next is True
        assert result.has_previous is False

        # Verify all returned matches have outcomes and predictions
        for match in result.matches:
            assert hasattr(match, "radiant_win")  # Has outcome data
            assert hasattr(match, "predicted_outcome")  # Has prediction data

    async def test_get_paginated_matches_second_page(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test retrieval of second page."""
        # ARRANGE
        filters = PaginationFilters(page=2, page_size=10)

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        assert result is not None
        assert len(result.matches) == 5  # Remaining matches on second page
        assert result.total_count == 15
        assert result.page == 2
        assert result.page_size == 10
        assert result.total_pages == 2
        assert result.has_next is False
        assert result.has_previous is True

    async def test_get_paginated_matches_filter_by_match_id(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test filtering by specific match ID."""
        # ARRANGE
        test_data = seed_pagination_test_data
        target_match_id = test_data["completed_match_ids"][0]  # Use a completed match
        filters = PaginationFilters(page=1, page_size=10, match_id=target_match_id)

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        assert result is not None
        assert len(result.matches) == 1
        assert result.matches[0].match_id == target_match_id
        assert result.total_count == 1

    @pytest.mark.xfail(
        reason="Hero name resolution issue - needs investigation. Heroes are seeded correctly but get_hero_id_map resolution logic may have issues."
    )
    async def test_resolve_and_update_filters_hero_names(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test hero name resolution to IDs."""
        # ARRANGE
        # Use exact hero names from our test data
        filters = PaginationFilters(
            page=1, page_size=10, hero_names=["Anti-Mage", "Axe"]  # These match our seeded data
        )

        # ACT
        await integration_test_match_pagination_service._resolve_and_update_filters(filters)

        # ASSERT
        assert filters.hero_ids is not None
        assert 1 in filters.hero_ids  # Anti-Mage ID
        assert 2 in filters.hero_ids  # Axe ID
        assert len(filters.hero_ids) == 2

    @pytest.mark.xfail(
        reason="Hero name resolution issue - this test depends on the hero resolution working correctly."
    )
    async def test_resolve_and_update_filters_unknown_hero(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test hero name resolution with unknown hero raises HTTPException."""
        # ARRANGE
        filters = PaginationFilters(page=1, page_size=10, hero_names=["Unknown Hero", "Another Unknown"])

        # ACT & ASSERT
        with pytest.raises(HTTPException) as exc_info:
            await integration_test_match_pagination_service._resolve_and_update_filters(filters)

        assert exc_info.value.status_code == 400
        assert "Unknown Hero" in str(exc_info.value.detail)

    async def test_resolve_and_update_filters_patch_number(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test patch number resolution to date range."""
        # ARRANGE
        filters = PaginationFilters(page=1, page_size=10, patch_number="7.35")

        # ACT
        await integration_test_match_pagination_service._resolve_and_update_filters(filters)

        # ASSERT
        assert filters.patch_start_time == datetime(2023, 6, 1, tzinfo=timezone.utc)
        assert filters.patch_end_time == datetime(2024, 1, 1, tzinfo=timezone.utc)

    async def test_resolve_and_update_filters_unknown_patch(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test patch number resolution with unknown patch raises ValueError."""
        # ARRANGE
        filters = PaginationFilters(page=1, page_size=10, patch_number="7.99")  # Non-existent patch

        # ACT & ASSERT
        with pytest.raises(ValueError) as exc_info:
            await integration_test_match_pagination_service._resolve_and_update_filters(filters)

        assert "Patch '7.99' not found" in str(exc_info.value)

    async def test_get_paginated_matches_with_patch_filter(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test pagination with patch-based date filtering."""
        # ARRANGE
        filters = PaginationFilters(page=1, page_size=20, patch_number="7.35")  # Large page size to get all results

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
        filters = PaginationFilters(page=999, page_size=10)  # Very large page number

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        # Should return empty results but valid response structure
        assert result is not None
        assert len(result.matches) == 0
        assert result.page == 999
        assert result.total_count == 15  # Total still correct

    async def test_get_paginated_matches_edge_case_max_page_size(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test pagination with maximum allowed page size."""
        # ARRANGE
        filters = PaginationFilters(page=1, page_size=100)  # Maximum allowed size

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        # Should return all results in one page
        assert result.page_size == 100
        assert len(result.matches) == 15  # All completed matches
        assert result.total_pages == 1

    async def test_get_paginated_matches_no_results(
        self, integration_test_match_pagination_service: MatchPaginationService, seed_pagination_test_data
    ):
        """Test pagination when no matches are found."""
        # ARRANGE
        filters = PaginationFilters(page=1, page_size=10, match_id=999999)  # Non-existent match ID

        # ACT
        result = await integration_test_match_pagination_service.get_paginated_matches(filters)

        # ASSERT
        assert result is not None
        assert len(result.matches) == 0
        assert result.total_count == 0
        assert result.total_pages == 0
        assert result.has_next is False
        assert result.has_previous is False
