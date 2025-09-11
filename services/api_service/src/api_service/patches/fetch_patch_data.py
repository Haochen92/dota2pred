from api_service.dependencies import DatabaseSession
from dota_oracle_common.utils import get_logger
from dota_oracle_common.models.api.schema import PatchDataAPIResponse
from dota_oracle_common.repositories.patch_repository import PatchRepository


logger = get_logger(__name__)


async def fetch_patch_ids(db_session: DatabaseSession) -> PatchDataAPIResponse:
    """Fetch all available patch identifiers from the database."""
    patch_repo = PatchRepository(db_session)
    patch_mapping = await patch_repo.get_patch_mapping()
    # Sort for stable output
    patch_ids = sorted(patch_mapping.keys(), reverse=True)
    return PatchDataAPIResponse(patches=patch_ids)
