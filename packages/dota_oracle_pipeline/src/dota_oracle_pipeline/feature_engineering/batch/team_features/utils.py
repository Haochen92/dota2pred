from typing import List, Optional, Tuple

from dota_oracle_common.models.match.table import MatchTable


def default_winrate(alpha: int, beta: int) -> float:
    return alpha / beta


def sorted_by_start_time(all_matches: List[MatchTable]) -> List[MatchTable]:
    return sorted(all_matches, key=lambda m: m.start_time)


def ts(dt) -> int:
    return int(dt.timestamp())


def get_radiant_won(match: MatchTable) -> Optional[bool]:
    return match.outcome.radiant_win if match.outcome else None


def apply_decay_to_pair(
    wins: float, games: float, last_ts: int, now_ts: int, half_life_days: float
) -> Tuple[float, float]:
    if now_ts <= last_ts:
        return wins, games
    delta_seconds = now_ts - last_ts
    factor = 0.5 ** (delta_seconds / (half_life_days * 86400.0))
    return wins * factor, games * factor


def get_matchup_key(id1: int, id2: int) -> Tuple[int, int]:
    return tuple(sorted((id1, id2)))


def get_matchup_key_and_outcome(rad_id: int, dire_id: int, radiant_won: bool) -> Tuple[Tuple[int, int], bool]:
    key = tuple(sorted((rad_id, dire_id)))
    t1_won = radiant_won if rad_id == key[0] else not radiant_won
    return key, t1_won
