"""
Configuration and fixtures for API services integration tests.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, Dict
from datetime import datetime, timezone

from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(scope="function")
async def seed_pagination_test_data(
    db_session: AsyncSession,
    match_table_factory,
    match_outcome_table_factory,
    match_prediction_table_factory,
    hero_data_table_factory,
    patch_table_factory,
) -> AsyncGenerator[Dict, None]:
    """Seed database with comprehensive test data for match pagination testing."""

    # Create hero data
    heroes = [
        hero_data_table_factory.build(id=1, localized_name="Anti-Mage"),
        hero_data_table_factory.build(id=2, localized_name="Axe"),
        hero_data_table_factory.build(id=3, localized_name="Bane"),
        hero_data_table_factory.build(id=4, localized_name="Bloodseeker"),
        hero_data_table_factory.build(id=5, localized_name="Crystal Maiden"),
    ]

    # Create patch data
    patches = [
        patch_table_factory.build(
            patch_number="7.34",
            start_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2023, 6, 1, tzinfo=timezone.utc),
        ),
        patch_table_factory.build(
            patch_number="7.35",
            start_time=datetime(2023, 6, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        patch_table_factory.build(
            patch_number="7.36", start_time=datetime(2024, 1, 1, tzinfo=timezone.utc), end_time=None  # Current patch
        ),
    ]

    # Create matches with different scenarios
    match_ids = list(range(100001, 100021))  # 20 matches
    matches = []
    outcomes = []
    predictions = []

    for i, match_id in enumerate(match_ids):
        # Create match
        match = match_table_factory.build(
            match_id=match_id,
            start_time=(
                datetime(2023, 6, 15, tzinfo=timezone.utc) if i < 10 else datetime(2024, 2, 15, tzinfo=timezone.utc)
            ),
        )
        matches.append(match)

        # Create outcome for completed matches (first 15 matches)
        if i < 15:
            outcome = match_outcome_table_factory.build(match_id=match_id, radiant_win=(i % 2 == 0))  # Alternate wins
            outcomes.append(outcome)

            # Create prediction for matches with outcomes
            prediction = match_prediction_table_factory.build(
                match_id=match_id, prediction=(i % 3 != 0)  # Varied predictions
            )
            predictions.append(prediction)

    # Add all data to session
    db_session.add_all(heroes + patches + matches + outcomes + predictions)
    await db_session.flush()

    logger.info(
        f"Seeded {len(heroes)} heroes, {len(patches)} patches, {len(matches)} matches, "
        f"{len(outcomes)} outcomes, and {len(predictions)} predictions"
    )

    yield {
        "heroes": {hero.id: hero for hero in heroes},
        "patches": {patch.patch_number: patch for patch in patches},
        "matches": {match.match_id: match for match in matches},
        "outcomes": {outcome.match_id: outcome for outcome in outcomes},
        "predictions": {pred.match_id: pred for pred in predictions},
        "match_ids": match_ids,
        "completed_match_ids": match_ids[:15],
        "ongoing_match_ids": match_ids[15:],
    }
