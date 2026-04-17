from __future__ import annotations

from typing import List, Dict, Tuple
import numpy as np
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from dota_oracle_common.models.api.schema import PublicMatchPredictionDTO
from dota_oracle_common.models.match import PublicMatchTable

# --- Helper Function 1: Core Stat Aggregation Logic ---


def _process_team_stats(
    heroes: List[int],
    team_won: bool,
    target_heroes: set[int],
    factor: float,
    wins: Dict[int, float],
    games: Dict[int, float],
) -> None:
    for hero_id in heroes:
        if hero_id in target_heroes:
            games[hero_id] += factor
            if team_won:
                wins[hero_id] += factor


def _calculate_decayed_hero_stats(
    rows: List[PublicMatchTable],
    target_heroes: set[int],
    start_time: datetime,
    half_life_days: float,
) -> Tuple[Dict[int, float], Dict[int, float]]:
    """
    Calculates time-decayed statistics (wins and games) for a set of target heroes.

    Args:
        rows: A list of historical match data from the database.
        target_heroes: The set of hero IDs whose stats we want to track.
        start_time: The timestamp of the new match, used as the 'present' for decay calculations.
        half_life_days: The half-life for the exponential time decay.

    Returns:
        A tuple containing two dictionaries: (total_decayed_wins, total_decayed_games).
    """
    total_decayed_wins: Dict[int, float] = {h: 0.0 for h in target_heroes}
    total_decayed_games: Dict[int, float] = {h: 0.0 for h in target_heroes}

    now_ts = start_time.timestamp()
    half_life_seconds = half_life_days * 86400.0 if half_life_days > 0 else None

    for row in rows:
        match_ts = row.start_time.timestamp()

        # Calculate the decay factor for this historical match
        if half_life_seconds and now_ts > match_ts:
            factor = 0.5 ** ((now_ts - match_ts) / half_life_seconds)
        else:
            factor = 1.0

        # Process Radiant Team
        radiant_heroes = [
            row.slot_0_hero_id,
            row.slot_1_hero_id,
            row.slot_2_hero_id,
            row.slot_3_hero_id,
            row.slot_4_hero_id,
        ]
        _process_team_stats(
            heroes=radiant_heroes,
            team_won=bool(row.radiant_win),
            target_heroes=target_heroes,
            factor=factor,
            wins=total_decayed_wins,
            games=total_decayed_games,
        )

        # Process Dire Team
        dire_heroes = [
            row.slot_128_hero_id,
            row.slot_129_hero_id,
            row.slot_130_hero_id,
            row.slot_131_hero_id,
            row.slot_132_hero_id,
        ]
        _process_team_stats(
            heroes=dire_heroes,
            team_won=not bool(row.radiant_win),
            target_heroes=target_heroes,
            factor=factor,
            wins=total_decayed_wins,
            games=total_decayed_games,
        )

    return total_decayed_wins, total_decayed_games


def _smoothed_wr(
    hero_id: int,
    wins: Dict[int, float],
    games: Dict[int, float],
    prior_mean: float,
    prior_count: float,
) -> float:
    """
    Calculates the Bayesian-smoothed win rate for a single hero using a weighted average
    between the prior belief and the observed (decayed) data.
    """
    hero_wins = wins.get(hero_id, 0.0)
    hero_games = games.get(hero_id, 0.0)

    prior_win_rate = prior_mean
    prior_weight = prior_count

    if hero_games <= 1e-6:
        return prior_win_rate

    data_win_rate = hero_wins / hero_games
    data_weight = hero_games

    # Step 2: Perform the weighted average calculation
    total_weighted_wins = (prior_win_rate * prior_weight) + (data_win_rate * data_weight)
    total_weight = prior_weight + data_weight

    return total_weighted_wins / total_weight


def _calculate_feature_from_stats(
    wins: Dict[int, float],
    games: Dict[int, float],
    dto: PublicMatchPredictionDTO,
    prior_mean: float,
    prior_count: float,
) -> float:
    """
    Calculates the final feature value from the aggregated stats using Bayesian smoothing.

    Args:
        wins: Dictionary of decayed wins per hero.
        games: Dictionary of decayed games per hero.
        dto: The request DTO containing the radiant and dire hero lists.
        prior_mean: The prior win rate for the Bayesian smoothing.
        prior_count: The weight of the prior (virtual past games).

    Returns:
        The final feature value (radiant_wr_sum - dire_wr_sum).
    """
    radiant_sum = sum(
        _smoothed_wr(h, wins=wins, games=games, prior_mean=prior_mean, prior_count=prior_count)
        for h in dto.radiant_heroes
    )
    dire_sum = sum(
        _smoothed_wr(h, wins=wins, games=games, prior_mean=prior_mean, prior_count=prior_count) for h in dto.dire_heroes
    )

    return radiant_sum - dire_sum


async def create_public_inference_features(
    session: AsyncSession,
    dto: PublicMatchPredictionDTO,
    *,
    prior_mean: float = 0.5,
    prior_count: float = 50.0,
    half_life_days: float = 60.0,
    recent_match_limit: int = 50000,
) -> np.ndarray:
    """
    Orchestrates the computation of model-ready features for public inference.

    Steps:
    1. Fetches recent historical match data from the database.
    2. Delegates to a helper to aggregate decayed win/loss stats for relevant heroes.
    3. Delegates to another helper to compute the final feature using the aggregated stats.
    4. Formats and returns the result as a numpy array.
    """
    target_heroes = set(dto.radiant_heroes + dto.dire_heroes)
    if not target_heroes:
        return np.array([[0.0]], dtype=np.float64)

    # Step 1: Fetch historical data
    stmt = (
        select(PublicMatchTable)
        .where(PublicMatchTable.start_time < dto.start_time)
        .order_by(desc(PublicMatchTable.start_time))
        .limit(recent_match_limit)
    )
    result = await session.execute(stmt)
    rows: List[PublicMatchTable] = list(result.scalars().all())

    # Handle case with no historical data
    if not rows:
        feature_value = (prior_mean * 5) - (prior_mean * 5)  # which is 0.0
        return np.array([[feature_value]], dtype=np.float64)

    # Step 2: Aggregate decayed stats using a dedicated helper
    wins, games = _calculate_decayed_hero_stats(
        rows=rows,
        target_heroes=target_heroes,
        start_time=dto.start_time,
        half_life_days=half_life_days,
    )

    # Step 3: Compute the final feature from the aggregated stats
    hero_wr_diff = _calculate_feature_from_stats(
        wins=wins,
        games=games,
        dto=dto,
        prior_mean=prior_mean,
        prior_count=prior_count,
    )

    # Step 4: Format and return
    return np.array([[hero_wr_diff]], dtype=np.float64)
