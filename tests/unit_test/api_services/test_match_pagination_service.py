"""
Unit tests for the MatchPaginationService.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from dota_oracle_common.models.pagination import PaginationFilters


@pytest.mark.asyncio
async def test_get_paginated_matches_successfully(
    unit_test_match_pagination_service,
    match_table_factory,
    match_prediction_table_factory,
    mocker,
) -> None:
    filters = PaginationFilters(offset=0, limit=10)

    mock_matches = match_table_factory.batch(5)
    for i, match in enumerate(mock_matches):
        mock_prediction = match_prediction_table_factory.build(prediction=True)
        match.predictions = [mock_prediction]

        mock_outcome = mocker.MagicMock()
        mock_outcome.radiant_win = i % 2 == 0
        match.outcome = mock_outcome

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_matches

    mock_count_result = MagicMock()
    mock_count_result.scalar_one_or_none.return_value = 25
    unit_test_match_pagination_service.session.execute.side_effect = [mock_count_result, mock_result]

    mock_resolve_filters = mocker.patch.object(unit_test_match_pagination_service, "_resolve_patch_filters")
    mock_apply_filters = mocker.patch.object(
        unit_test_match_pagination_service,
        "_apply_filters",
        side_effect=lambda query, current_filters: query,
    )

    result = await unit_test_match_pagination_service.get_paginated_matches(filters)

    assert len(result.matches) == 5
    assert result.total_count == 25
    assert result.total_pages == 3
    assert result.page is None
    assert result.page_size is None
    mock_resolve_filters.assert_awaited_once_with(filters)
    mock_apply_filters.assert_called_once()


@pytest.mark.asyncio
async def test_get_paginated_matches_returns_empty_when_limit_is_not_requested(
    unit_test_match_pagination_service,
    mocker,
) -> None:
    filters = PaginationFilters()

    mock_count_result = MagicMock()
    mock_count_result.scalar_one_or_none.return_value = 25
    unit_test_match_pagination_service.session.execute.return_value = mock_count_result

    mocker.patch.object(unit_test_match_pagination_service, "_resolve_patch_filters")
    mocker.patch.object(
        unit_test_match_pagination_service, "_apply_filters", side_effect=lambda query, current_filters: query
    )

    result = await unit_test_match_pagination_service.get_paginated_matches(filters)

    assert result.matches == []
    assert result.total_count == 25
    assert result.total_pages == 0


@pytest.mark.asyncio
async def test_resolve_patch_filters_success(
    unit_test_match_pagination_service,
    patch_table_factory,
) -> None:
    filters = PaginationFilters(offset=0, limit=20, patch_number="7.35")
    mock_patch = patch_table_factory.build(
        patch_number="7.35",
        start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2024, 3, 1, tzinfo=timezone.utc),
    )
    unit_test_match_pagination_service.patch_repository.get_patch_by_number.return_value = mock_patch

    await unit_test_match_pagination_service._resolve_patch_filters(filters)

    assert filters.patch_start_time == datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert filters.patch_end_time == datetime(2024, 3, 1, tzinfo=timezone.utc)
    unit_test_match_pagination_service.patch_repository.get_patch_by_number.assert_awaited_once_with("7.35")


@pytest.mark.asyncio
async def test_resolve_patch_filters_raises_for_unknown_patch(unit_test_match_pagination_service) -> None:
    filters = PaginationFilters(offset=0, limit=20, patch_number="7.99")
    unit_test_match_pagination_service.patch_repository.get_patch_by_number.return_value = None

    with pytest.raises(ValueError, match="Patch '7.99' not found"):
        await unit_test_match_pagination_service._resolve_patch_filters(filters)


def test_apply_filters_match_id(unit_test_match_pagination_service, pagination_filters_factory, mocker) -> None:
    filters = pagination_filters_factory.build(match_id=123456)
    mock_query = mocker.MagicMock()

    unit_test_match_pagination_service._apply_filters(mock_query, filters)

    mock_query.where.assert_called_once()


def test_apply_filters_team_name(unit_test_match_pagination_service, pagination_filters_factory, mocker) -> None:
    filters = pagination_filters_factory.build(team_name="Team Secret")
    mock_query = mocker.MagicMock()

    unit_test_match_pagination_service._apply_filters(mock_query, filters)

    mock_query.where.assert_called_once()


def test_apply_filters_hero_ids(unit_test_match_pagination_service, pagination_filters_factory, mocker) -> None:
    filters = pagination_filters_factory.build(hero_ids=[1, 2, 3])
    mock_query = mocker.MagicMock()

    unit_test_match_pagination_service._apply_filters(mock_query, filters)

    mock_query.where.assert_called_once()


def test_apply_filters_no_conditions(unit_test_match_pagination_service, mocker) -> None:
    filters = PaginationFilters(offset=0, limit=20, match_id=None, team_name=None, team_ids=None, hero_ids=None)
    mock_query = mocker.MagicMock()

    result_query = unit_test_match_pagination_service._apply_filters(mock_query, filters)

    assert result_query == mock_query
    mock_query.where.assert_not_called()
