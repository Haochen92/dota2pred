from typing import List
from dota_oracle_common.models.patches.schema import DotaPatch
from dota_oracle_common.models.patches.table import PatchTable
from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)


def calculate_patch_end_times(patches: List[DotaPatch]) -> List[PatchTable]:
    """
    Calculate end times for patches and convert to PatchTable instances.

    End time is set to the start time of the next patch (sorted by start_time).
    The latest patch has end_time = None.

    Args:
        patches: List of DotaPatch instances from API

    Returns:
        List of PatchTable instances with calculated end_time
    """
    if not patches:
        logger.warning("No patches provided for end time calculation")
        return []

    # Sort patches by start_time to ensure correct ordering
    sorted_patches = sorted(patches, key=lambda p: p.start_time)

    patch_tables = []

    for i, patch in enumerate(sorted_patches):
        # Calculate end_time as the start_time of the next patch
        end_time = None
        if i + 1 < len(sorted_patches):
            end_time = sorted_patches[i + 1].start_time

        # Create PatchTable instance with calculated end_time
        patch_table = PatchTable(id=patch.id, patch_number=patch.name, start_time=patch.start_time, end_time=end_time)

        patch_tables.append(patch_table)

        logger.debug(f"Patch {patch.name}: start={patch.start_time}, end={end_time or 'None (latest)'}")

    logger.info(f"Calculated end times for {len(patch_tables)} patches")
    return patch_tables


def update_patch_end_times(existing_patches: List[PatchTable]) -> List[PatchTable]:
    """
    Recalculate end times for existing PatchTable instances.

    Useful when new patches are added and existing end times need to be updated.

    Args:
        existing_patches: List of existing PatchTable instances

    Returns:
        List of PatchTable instances with updated end_time
    """
    if not existing_patches:
        logger.warning("No existing patches provided for end time update")
        return []

    # Sort patches by start_time
    sorted_patches = sorted(existing_patches, key=lambda p: p.start_time)

    # Update end times
    for i, patch in enumerate(sorted_patches):
        # Calculate end_time as the start_time of the next patch
        if i + 1 < len(sorted_patches):
            patch.end_time = sorted_patches[i + 1].start_time
        else:
            # Latest patch has no end time
            patch.end_time = None

    logger.info(f"Updated end times for {len(sorted_patches)} patches")
    return sorted_patches
