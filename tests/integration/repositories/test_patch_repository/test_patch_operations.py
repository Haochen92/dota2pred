import pytest
from datetime import datetime, timezone
from typing import List

from ..base_test_repository import BaseTestRepository
from dota_oracle_common.repositories.patch_repository import PatchRepository
from dota_oracle_common.models.patches.table import PatchTable
from dota_oracle_common.utils import get_logger

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestStorePatchTables:
    """Test class for patch data storage operations."""

    async def test_store_new_patches_successfully(
        self,
        patch_repository_test_subject: PatchRepository,
        test_repository: BaseTestRepository,
        patch_table_factory,
    ):
        """Test storing new patch data successfully inserts records."""
        # ARRANGE
        new_patches = [
            patch_table_factory.build(
                id=10, patch_number="7.38", start_time=datetime(2024, 9, 1, tzinfo=timezone.utc), end_time=None
            ),
            patch_table_factory.build(
                id=11, patch_number="7.39", start_time=datetime(2024, 12, 1, tzinfo=timezone.utc), end_time=None
            ),
        ]

        # ACT
        await patch_repository_test_subject.store_patch_tables(new_patches)

        # ASSERT - Verify data was stored
        stored_patches = await test_repository._get_data(model_class=PatchTable, id_filters=[10, 11])

        test_repository._assert_count_equal(
            actual_count=len(stored_patches),
            expected_count=len(new_patches),
            test_scenario="store_new_patches - record count",
        )

        # Verify patch details
        stored_patch_numbers = {patch.patch_number for patch in stored_patches}
        expected_patch_numbers = {patch.patch_number for patch in new_patches}
        assert stored_patch_numbers == expected_patch_numbers

    async def test_upsert_existing_patches(
        self,
        patch_repository_test_subject: PatchRepository,
        test_repository: BaseTestRepository,
        patch_table_factory,
    ):
        """Test upserting existing patch data updates records correctly."""
        # ARRANGE - Initial patch
        initial_patch = patch_table_factory.build(
            id=20, patch_number="7.40", start_time=datetime(2024, 8, 1, tzinfo=timezone.utc), end_time=None
        )

        # ACT - Initial insert
        await patch_repository_test_subject.store_patch_tables([initial_patch])

        # Verify initial insert
        stored_patches = await test_repository._get_data(model_class=PatchTable, id_filters=[20])
        assert len(stored_patches) == 1
        assert stored_patches[0].end_time is None

        # ACT - Update with end_time
        updated_patch = patch_table_factory.build(
            id=20,
            patch_number="7.40",
            start_time=datetime(2024, 8, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, tzinfo=timezone.utc),
        )
        await patch_repository_test_subject.store_patch_tables([updated_patch])

        # ASSERT - Verify update
        updated_stored_patches = await test_repository._get_data(model_class=PatchTable, id_filters=[20])

        test_repository._assert_count_equal(
            actual_count=len(updated_stored_patches),
            expected_count=1,
            test_scenario="upsert_existing_patches - record count",
        )

        updated_stored_patch = updated_stored_patches[0]
        assert updated_stored_patch.end_time == datetime(2024, 11, 1, tzinfo=timezone.utc)

    async def test_store_empty_list_handles_gracefully(
        self,
        patch_repository_test_subject: PatchRepository,
    ):
        """Test storing empty list is handled gracefully."""
        # ACT & ASSERT - Should not raise exception
        await patch_repository_test_subject.store_patch_tables([])


class TestGetPatchByNumber:
    """Test class for retrieving patch by number."""

    async def test_get_existing_patch_by_number(
        self,
        patch_repository_test_subject: PatchRepository,
        seed_patch_data: List[PatchTable],
    ):
        """Test retrieving existing patch by patch number."""
        # ACT
        patch = await patch_repository_test_subject.get_patch_by_number("7.35")

        # ASSERT
        assert patch is not None
        assert patch.patch_number == "7.35"
        assert patch.id == 101

    async def test_get_nonexistent_patch_returns_none(
        self,
        patch_repository_test_subject: PatchRepository,
        seed_patch_data: List[PatchTable],
    ):
        """Test retrieving non-existent patch returns None."""
        # ACT
        patch = await patch_repository_test_subject.get_patch_by_number("7.99")

        # ASSERT
        assert patch is None


class TestGetPatchMapping:
    """Test class for retrieving patch mapping."""

    async def test_get_patch_mapping_returns_correct_data(
        self,
        patch_repository_test_subject: PatchRepository,
        seed_patch_data: List[PatchTable],
    ):
        """Test retrieving patch mapping returns correct data."""
        # ACT
        patch_mapping = await patch_repository_test_subject.get_patch_mapping()

        # ASSERT
        assert len(patch_mapping) == 3

        # Verify specific mappings
        assert "7.35" in patch_mapping
        assert "7.36" in patch_mapping
        assert "7.37" in patch_mapping

        assert patch_mapping["7.35"] == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert patch_mapping["7.36"] == datetime(2024, 3, 1, tzinfo=timezone.utc)
        assert patch_mapping["7.37"] == datetime(2024, 6, 1, tzinfo=timezone.utc)


class TestGetOperationsEmptyDatabase:
    """Test class for operations on empty database."""

    async def test_get_patch_mapping_empty_database(
        self,
        patch_repository_test_subject: PatchRepository,
    ):
        """Test retrieving patch mapping from empty database returns empty dict."""
        # ACT
        patch_mapping = await patch_repository_test_subject.get_patch_mapping()

        # ASSERT
        assert patch_mapping == {}
