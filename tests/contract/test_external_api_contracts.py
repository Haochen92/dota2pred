"""
Contract Testing - Validate External Api response structure against pydantic models
"""

import pytest

# import api endpoints
from dota_oracle_pipeline.data_extraction import (
    fetch_hero_data,
    fetch_league_data,
    fetch_live_league_games,
    fetch_pro_match,
    fetch_match_details,
    fetch_patch_data,
)

# import pydantic api_models
from dota_oracle_common.models.match import MatchesAPIResponse
from dota_oracle_common.models.inference import ModelMetaDataAPIResponse
from dota_oracle_common.models.patches.schema import DotaPatch
from tenacity import retry, wait_fixed, stop_after_attempt

pytestmark = [pytest.mark.asyncio, pytest.mark.contract]

wait_duration = 20


@retry(stop=stop_after_attempt(3), wait=wait_fixed(wait_duration))
async def test_heroes_api_contract() -> None:
    hero_data = await fetch_hero_data()

    assert isinstance(hero_data, dict), f"expected dictionary, got {type(hero_data.__name__)}"

    assert hero_data, "returned hero data should not be empty"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(wait_duration))
async def test_league_api_contract() -> None:
    list_league_item = await fetch_league_data()

    assert isinstance(list_league_item, list), f"expected list, got {type(list_league_item.__name__)}"

    assert list_league_item, "returned list_league_item data should not be empty"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(wait_duration))
async def test_live_league_contract() -> None:
    games_list = await fetch_live_league_games()

    assert isinstance(games_list, list), f"expected list, got {type(games_list.__name__)}"

    assert games_list, "returned games_list data should not be empty"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(wait_duration))
async def test_match_details_contract() -> None:
    valid_match_id = 8320876321

    match_details = await fetch_match_details(valid_match_id)

    assert isinstance(
        match_details, MatchesAPIResponse
    ), f"expected type {MatchesAPIResponse.__name__}, got {type(match_details).__name__}"

    assert match_details


@retry(stop=stop_after_attempt(3), wait=wait_fixed(wait_duration))
async def test_pro_match_contract() -> None:
    valid_max, valid_min = 8320876321 + 1, 8320876321

    pro_match_list = await fetch_pro_match(valid_max, valid_min)  # Fetch one batch of data only

    assert isinstance(pro_match_list, list), f"expect list, got {type(pro_match_list).__name__}"

    assert len(pro_match_list) > 0, f"Results not expected to be 0, got {len(pro_match_list)}"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(wait_duration))
async def test_patch_api_contract() -> None:
    patch_data = await fetch_patch_data()

    assert isinstance(patch_data, list), f"expected list, got {type(patch_data).__name__}"

    assert patch_data, "returned patch data should not be empty"

    # Verify each patch is a DotaPatch instance
    for patch in patch_data:
        assert isinstance(patch, DotaPatch), f"expected DotaPatch instance, got {type(patch).__name__}"
        assert hasattr(patch, "name"), "patch should have 'name' attribute"
        assert hasattr(patch, "id"), "patch should have 'id' attribute"
        assert hasattr(patch, "start_time"), "patch should have 'start_time' attribute"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(wait_duration))
async def test_model_metadata_contract(unit_test_model_inference_service) -> None:
    # Test the metadata that's already injected in the service
    model_metadata = unit_test_model_inference_service.model_metadata

    assert isinstance(model_metadata, ModelMetaDataAPIResponse)
    assert model_metadata.version_metadata.feature_columns, "feature_columns is None"
    assert isinstance(model_metadata.version_metadata.feature_columns, list)
