from pydantic import BaseModel


class HeroWinrateTable(BaseModel):
    """
    Per-match features derived from aggregate hero win rates, computed causally
    (only using history BEFORE the match).
    """

    match_id: int
    radiant_avg_hero_winrate: float
    dire_avg_hero_winrate: float
    radiant_max_hero_winrate: float
    dire_max_hero_winrate: float
