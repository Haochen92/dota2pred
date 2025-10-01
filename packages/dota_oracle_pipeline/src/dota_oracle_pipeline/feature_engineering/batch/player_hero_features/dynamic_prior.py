from typing import Dict, List, Tuple, Optional

from dota_oracle_common.models.features.table import PlayerHeroFeatureTable
from dota_oracle_common.models.match.table import MatchTable

from .utils import (
    PLAYER_SLOTS,
    RADIANT_SLOTS,
    PlayerHeroDecayState,
    apply_decay_to_pair,
    default_winrate,
    get_player_hero_key,
    get_radiant_won,
    read_wr_decay,
    read_wr_decay_dynamic,
    sorted_by_start_time,
    ts,
    update_state_decay,
)


class PlayerHeroDynamicPriorFeatureGenerator:
    """Builds features using dynamic hero priors and player history.

    Generates features using dynamic priors for each player-hero history.

    Args:
        player_credibility_C (int): Strength of the prior at the player level.
        player_half_life_days (float): Half-life for player-hero decay.
        hero_alpha (int): Prior wins for hero-level Bayesian smoothing.
        hero_beta (int): Prior games for hero-level Bayesian smoothing.
        hero_half_life_days (float): Half-life for hero-level decay.
    """

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        player_credibility_C: int = 20,
        player_half_life_days: float = 45.0,
        hero_alpha: int = 5,
        hero_beta: int = 10,
        hero_half_life_days: float = 90.0,
    ) -> List[PlayerHeroFeatureTable]:
        if not all_matches:
            return []

        matches = sorted_by_start_time(all_matches)

        print("Step 1/2: Generating dynamic hero priors...")
        hero_priors = self._generate_hero_priors(
            matches,
            alpha=hero_alpha,
            beta=hero_beta,
            half_life_days=hero_half_life_days,
        )
        print("Hero priors generated.")

        print("Step 2/2: Generating player-hero features with dynamic priors...")
        ph_states: Dict[Tuple[int, int], PlayerHeroDecayState] = {}
        features: List[PlayerHeroFeatureTable] = []

        for match in matches:
            now_ts = ts(match.start_time)
            match_priors = hero_priors.get(match.match_id, {})

            fields: Dict[str, float] = {}
            for slot in PLAYER_SLOTS:
                key = get_player_hero_key(match, slot)
                if key[0] is None or key[1] is None:
                    fields[f"player_hero_{slot}_win_rate"] = 0.5
                    continue

                _, hero_id = key
                state = ph_states.get(key)
                prior_rate = match_priors.get(hero_id, 0.5)

                win_rate = read_wr_decay_dynamic(
                    state, now_ts, player_credibility_C, player_half_life_days, prior_rate
                )
                fields[f"player_hero_{slot}_win_rate"] = win_rate

            features.append(PlayerHeroFeatureTable(match_id=match.match_id, **fields))

            radiant_won = get_radiant_won(match)
            if radiant_won is not None:
                for slot in PLAYER_SLOTS:
                    key = get_player_hero_key(match, slot)
                    if key[0] is None or key[1] is None:
                        continue
                    player_won = radiant_won if slot in RADIANT_SLOTS else not radiant_won
                    ph_states[key] = update_state_decay(
                        ph_states.get(key), now_ts, player_won, player_half_life_days
                    )

        print("Player-hero features generated.")
        return features

    # ---- hero priors -------------------------------------------------------

    def _generate_hero_priors(
        self,
        sorted_matches: List[MatchTable],
        *,
        alpha: int,
        beta: int,
        half_life_days: float,
    ) -> Dict[int, Dict[int, float]]:
        """Generates per-match hero priors from decayed global hero performance."""
        default_wr = default_winrate(alpha, beta)
        hero_state: Dict[int, PlayerHeroDecayState] = {}
        priors_lookup: Dict[int, Dict[int, float]] = {}

        for match in sorted_matches:
            cur_ts = ts(match.start_time)
            priors_lookup[match.match_id] = {}

            # Collect all heroes present in the match
            all_hero_ids_in_match = set()
            for slot in PLAYER_SLOTS:
                _, hero_id = get_player_hero_key(match, slot)
                if hero_id is not None:
                    all_hero_ids_in_match.add(hero_id)

            # Read priors before updating state (causal)
            for hero_id in all_hero_ids_in_match:
                win_rate = read_wr_decay(
                    hero_state.get(hero_id), cur_ts, alpha, beta, half_life_days, default_wr
                )
                priors_lookup[match.match_id][hero_id] = win_rate

            # Update hero-level states based on outcome
            radiant_won = get_radiant_won(match)
            if radiant_won is not None:
                for slot in PLAYER_SLOTS:
                    _, hero_id = get_player_hero_key(match, slot)
                    if hero_id is not None:
                        player_won = radiant_won if slot in RADIANT_SLOTS else not radiant_won
                        prev_state: Optional[PlayerHeroDecayState] = hero_state.get(hero_id)
                        hero_state[hero_id] = update_state_decay(
                            prev_state, cur_ts, player_won, half_life_days
                        )

        return priors_lookup
