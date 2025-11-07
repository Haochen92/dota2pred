from typing import Tuple


def apply_decay_to_pair(
    w_wins: float, w_games: float, last_ts: int, now_ts: int, half_life_days: float
) -> Tuple[float, float]:
    """Applies exponential decay to a (wins, games) pair between timestamps."""
    if now_ts <= last_ts:
        return w_wins, w_games
    if half_life_days <= 0:
        return w_wins, w_games

    delta_seconds = now_ts - last_ts
    factor = 0.5 ** (delta_seconds / (half_life_days * 86400.0))
    return w_wins * factor, w_games * factor
