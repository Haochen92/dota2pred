"""
Unit tests for the patch data scheduler functions.
"""

from contextlib import asynccontextmanager

import pytest
from unittest.mock import AsyncMock

from dota_oracle_schedules.data_fetching.fetch_patch_data import store_patch_data, patch_data_orchestrator
from pydantic import ValidationError


@asynccontextmanager
async def _database_resource(session_factory):
    yield session_factory


@pytest.mark.asyncio
async def test_store_patch_data_successfully(
    mock_async_session, mock_patch_repository, dota_patch_factory, patch_table_factory, mocker
) -> None:
    """Test successful storage of patch data."""
    # ARRANGE
    mock_patch_data = dota_patch_factory.batch(2)
    mock_patch_tables = patch_table_factory.batch(2)

    mock_calculate_patch_end_times = mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.calculate_patch_end_times", return_value=mock_patch_tables
    )

    mock_patch_repo_class = mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.PatchRepository", return_value=mock_patch_repository
    )

    # ACT
    await store_patch_data(mock_async_session, mock_patch_data)

    # ASSERT
    mock_calculate_patch_end_times.assert_called_once_with(mock_patch_data)
    mock_patch_repo_class.assert_called_once_with(mock_async_session)
    mock_patch_repository.store_patch_tables.assert_awaited_once_with(mock_patch_tables)


@pytest.mark.asyncio
async def test_store_patch_data_empty_list(mock_async_session) -> None:
    """Test handling of empty patch data list."""
    # ACT & ASSERT - Should not raise exception
    await store_patch_data(mock_async_session, [])


@pytest.mark.asyncio
async def test_store_patch_data_validation_error(mock_async_session, dota_patch_factory, mocker) -> None:
    """Test handling of ValidationError during patch processing."""
    # ARRANGE
    mock_patch_data = dota_patch_factory.batch(1)

    mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.calculate_patch_end_times",
        side_effect=ValidationError.from_exception_data("Test validation error", []),
    )

    # ACT & ASSERT
    with pytest.raises(ValidationError):
        await store_patch_data(mock_async_session, mock_patch_data)


@pytest.mark.asyncio
async def test_store_patch_data_storage_exception(
    mock_async_session, mock_patch_repository, dota_patch_factory, patch_table_factory, mocker
) -> None:
    """Test handling of exceptions during storage."""
    # ARRANGE
    mock_patch_data = dota_patch_factory.batch(1)
    mock_patch_tables = patch_table_factory.batch(1)

    mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.calculate_patch_end_times", return_value=mock_patch_tables
    )

    mock_patch_repository.store_patch_tables.side_effect = Exception("Database error")

    mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.PatchRepository", return_value=mock_patch_repository
    )

    # ACT & ASSERT
    with pytest.raises(Exception):
        await store_patch_data(mock_async_session, mock_patch_data)


@pytest.mark.asyncio
async def test_patch_data_orchestrator_success(mock_db_session_factory, dota_patch_factory, mocker) -> None:
    """Test successful execution of patch data orchestrator flow."""
    # ARRANGE
    mock_patch_data = dota_patch_factory.batch(2)

    mock_fetch_patch_data = mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.fetch_patch_data", return_value=mock_patch_data
    )

    mock_database_resource = mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.database_session_factory_resource",
        side_effect=lambda: _database_resource(mock_db_session_factory),
    )

    mock_store_patch_data = mocker.patch("dota_oracle_schedules.data_fetching.fetch_patch_data.store_patch_data")
    mock_hydrate = mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.hydrate_patch_boundaries_task",
        new_callable=AsyncMock,
        return_value=1,
    )

    # ACT
    await patch_data_orchestrator()

    # ASSERT
    mock_fetch_patch_data.assert_awaited_once()
    mock_database_resource.assert_called_once()
    mock_store_patch_data.assert_awaited_once()
    mock_hydrate.assert_awaited_once_with(mock_db_session_factory)


@pytest.mark.asyncio
async def test_patch_data_orchestrator_store_exception(mock_db_session_factory, dota_patch_factory, mocker) -> None:
    """Test orchestrator handles store_patch_data exceptions."""
    # ARRANGE
    mock_patch_data = dota_patch_factory.batch(1)

    mocker.patch("dota_oracle_schedules.data_fetching.fetch_patch_data.fetch_patch_data", return_value=mock_patch_data)

    mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.database_session_factory_resource",
        side_effect=lambda: _database_resource(mock_db_session_factory),
    )

    mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.store_patch_data", side_effect=Exception("Storage failed")
    )
    mock_hydrate = mocker.patch(
        "dota_oracle_schedules.data_fetching.fetch_patch_data.hydrate_patch_boundaries_task",
        new_callable=AsyncMock,
        return_value=0,
    )

    # ACT & ASSERT
    with pytest.raises(Exception):
        await patch_data_orchestrator()
    mock_hydrate.assert_not_awaited()
