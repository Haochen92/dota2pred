"""
Unit tests for the MatchPaginationService.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from fastapi import HTTPException

from dota_oracle_common.models.pagination import PaginationFilters


@pytest.mark.asyncio
async def test_get_paginated_matches_successfully(
    unit_test_match_pagination_service,
    pagination_filters_factory,
    match_table_factory,
    match_prediction_table_factory,
    mocker,
) -> None:
    """Test successful retrieval of paginated matches."""
    # ARRANGE
    filters = PaginationFilters(page=1, page_size=10)

    # Create matches with predictions and outcomes
    mock_matches = match_table_factory.batch(5)
    for i, match in enumerate(mock_matches):
        # Mock predictions list with at least one prediction
        mock_prediction = match_prediction_table_factory.build(prediction=True)
        match.predictions = [mock_prediction]

        # Mock outcome to match CompletedMatchAPIPayload requirements
        mock_outcome = mocker.MagicMock()
        mock_outcome.radiant_win = i % 2 == 0  # Alternate between radiant win/loss
        match.outcome = mock_outcome

    # Mock the database execution
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_matches

    # Mock count query result
    mock_count_result = MagicMock()
    mock_count_result.scalar_one_or_none.return_value = 25
    unit_test_match_pagination_service.session.execute.side_effect = [mock_count_result, mock_result]

    # Mock internal methods
    mock_resolve_filters = mocker.patch.object(unit_test_match_pagination_service, "_resolve_and_update_filters")
    mock_apply_filters = mocker.patch.object(
        unit_test_match_pagination_service, "_apply_filters", side_effect=lambda query, filters: query
    )

    # ACT
    result = await unit_test_match_pagination_service.get_paginated_matches(filters)

    # ASSERT
    assert len(result.matches) == 5
    assert result.total_count == 25
    assert result.page == 1
    assert result.page_size == 10
    assert result.total_pages == 3
    assert result.has_next is True
    assert result.has_previous is False

    mock_resolve_filters.assert_awaited_once_with(filters)
    mock_apply_filters.assert_called_once()


@pytest.mark.asyncio
async def test_get_paginated_matches_invalid_page_parameters(
    unit_test_match_pagination_service, pagination_filters_factory, mocker
) -> None:
    """Test pagination service handles invalid page parameters correctly."""
    # ARRANGE
    # Test valid but edge-case parameters that the service should handle
    filters = pagination_filters_factory.build(page=1, page_size=20)
    # Manually set invalid values after creation to test service handling
    filters.page = 0
    filters.page_size = 150

    # Mock database execution to return empty results
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_count_result = MagicMock()
    mock_count_result.scalar_one_or_none.return_value = 0
    unit_test_match_pagination_service.session.execute.side_effect = [mock_count_result, mock_result]

    # Mock internal methods
    mocker.patch.object(unit_test_match_pagination_service, "_resolve_and_update_filters")
    mocker.patch.object(unit_test_match_pagination_service, "_apply_filters", side_effect=lambda query, filters: query)

    # ACT
    result = await unit_test_match_pagination_service.get_paginated_matches(filters)

    # ASSERT
    # Page should be corrected to 1, page_size should be corrected to 20
    assert result.page == 1
    assert result.page_size == 20


@pytest.mark.asyncio
async def test_resolve_and_update_filters_hero_names_success(
    unit_test_match_pagination_service, pagination_filters_factory
) -> None:
    """Test successful hero name resolution to IDs."""
    # ARRANGE
    filters = PaginationFilters.model_validate({"hero_names[]": ["Anti-Mage", "Crystal Maiden"]})
    # The service now has hero_map directly, so no need to mock hero_repository

    # ACT
    await unit_test_match_pagination_service._resolve_and_update_filters(filters)

    # ASSERT
    assert filters.hero_ids == [1, 2]  # Based on the hero_map in the fixture


@pytest.mark.asyncio
async def test_resolve_and_update_filters_hero_names_not_found(
    unit_test_match_pagination_service, pagination_filters_factory
) -> None:
    """Test hero name resolution raises HTTPException for unknown heroes."""
    # ARRANGE
    filters = PaginationFilters.model_validate({"hero_names[]": ["Unknown Hero", "Another Unknown"]})
    # The service now has hero_map directly from the fixture

    # ACT & ASSERT
    with pytest.raises(HTTPException) as exc_info:
        await unit_test_match_pagination_service._resolve_and_update_filters(filters)

    assert exc_info.value.status_code == 400
    assert "Unknown Hero, Another Unknown" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_resolve_and_update_filters_patch_number_success(
    unit_test_match_pagination_service, pagination_filters_factory, patch_table_factory
) -> None:
    """Test successful patch number resolution to date range."""
    # ARRANGE
    filters = PaginationFilters(
        page=1,
        page_size=20,
        patch_number="7.35",
        match_id=None,
        team_name=None,
        team_ids=None,
        hero_names=None,  # Explicitly set to None to avoid hero resolution
        hero_ids=None,
        patch_start_time=None,
        patch_end_time=None,
    )
    mock_patch = patch_table_factory.build(
        patch_number="7.35",
        start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2024, 3, 1, tzinfo=timezone.utc),
    )
    unit_test_match_pagination_service.patch_repository.get_patch_by_number.return_value = mock_patch

    # ACT
    await unit_test_match_pagination_service._resolve_and_update_filters(filters)

    # ASSERT
    assert filters.patch_start_time == datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert filters.patch_end_time == datetime(2024, 3, 1, tzinfo=timezone.utc)
    unit_test_match_pagination_service.patch_repository.get_patch_by_number.assert_awaited_once_with("7.35")


@pytest.mark.asyncio
async def test_resolve_and_update_filters_patch_number_not_found(
    unit_test_match_pagination_service, pagination_filters_factory
) -> None:
    """Test patch number resolution raises ValueError for unknown patch."""
    # ARRANGE
    filters = PaginationFilters(
        page=1,
        page_size=20,
        patch_number="7.99",
        match_id=None,
        team_name=None,
        team_ids=None,
        hero_names=None,  # Explicitly set to None to avoid hero resolution
        hero_ids=None,
        patch_start_time=None,
        patch_end_time=None,
    )
    unit_test_match_pagination_service.patch_repository.get_patch_by_number.return_value = None

    # ACT & ASSERT
    with pytest.raises(ValueError) as exc_info:
        await unit_test_match_pagination_service._resolve_and_update_filters(filters)

    assert "Patch '7.99' not found" in str(exc_info.value)


def test_apply_filters_match_id(unit_test_match_pagination_service, pagination_filters_factory, mocker) -> None:
    """Test applying match_id filter."""
    # ARRANGE
    filters = pagination_filters_factory.build(match_id=123456)
    mock_query = mocker.MagicMock()

    # ACT
    unit_test_match_pagination_service._apply_filters(mock_query, filters)

    # ASSERT
    mock_query.where.assert_called_once()


def test_apply_filters_team_name(unit_test_match_pagination_service, pagination_filters_factory, mocker) -> None:
    """Test applying team_name filter."""
    # ARRANGE
    filters = pagination_filters_factory.build(team_name="Team Secret")
    mock_query = mocker.MagicMock()

    # ACT
    unit_test_match_pagination_service._apply_filters(mock_query, filters)

    # ASSERT
    mock_query.where.assert_called_once()


def test_apply_filters_hero_ids(unit_test_match_pagination_service, pagination_filters_factory, mocker) -> None:
    """Test applying hero_ids filter."""
    # ARRANGE
    filters = pagination_filters_factory.build(hero_ids=[1, 2, 3])
    mock_query = mocker.MagicMock()

    # ACT
    unit_test_match_pagination_service._apply_filters(mock_query, filters)

    # ASSERT
    mock_query.where.assert_called_once()


def test_apply_filters_no_conditions(unit_test_match_pagination_service, pagination_filters_factory, mocker) -> None:
    """Test applying filters with no conditions returns original query."""
    # ARRANGE
    # Explicitly set all filter fields to None/empty
    filters = PaginationFilters(
        page=1,
        page_size=20,
        match_id=None,
        team_name=None,
        team_ids=None,
        hero_ids=None,
        patch_start_time=None,
        patch_end_time=None,
    )
    mock_query = mocker.MagicMock()

    # ACT
    result_query = unit_test_match_pagination_service._apply_filters(mock_query, filters)

    # ASSERT
    # Should return the original query without calling where
    assert result_query == mock_query
    mock_query.where.assert_not_called()
