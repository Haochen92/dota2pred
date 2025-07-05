from pydantic import BaseModel, RootModel
from typing import Dict, List, Optional


class HeroData(BaseModel):
    """Hero data model with attributes, attack, armor and health stats.

    Attributes:
        primary_attr: Primary attribute (str, optional)
        agi_gain, base_agi: Agility stats (float, optional)
        int_gain, base_int: Intelligence stats (float, optional)
        str_gain, base_str: Strength stats (float, optional)
        attack_type, attack_rate, attack_range, attack_point, projectile_speed: Attack stats (str/float, optional)
        base_armor: Armor value (float, optional)
        base_mana, base_mana_regen: Mana stats (int/float, optional)
        base_health, base_health_regen: Health stats (int/float, optional)
        id: Unique hero identifier (int)
        localized_name: Hero display name (str)
        roles: Hero role list (List[str])
    """

    # Attributes
    primary_attr: Optional[str] = None
    agi_gain: Optional[float] = None
    base_agi: Optional[float] = None
    int_gain: Optional[float] = None
    base_int: Optional[float] = None
    str_gain: Optional[float] = None
    base_str: Optional[float] = None

    # Attack
    attack_type: Optional[str] = None
    attack_rate: Optional[float] = None
    attack_range: Optional[float] = None
    attack_point: Optional[float] = None
    projectile_speed: Optional[float] = None

    # Armour
    base_armor: Optional[float] = None

    # health and mana
    base_mana: Optional[int] = None
    base_mana_regen: Optional[float] = None
    base_health: Optional[int] = None
    base_health_regen: Optional[float] = None

    # id
    id: int
    localized_name: str
    roles: List[str] = []


class HeroesAPIResponse(RootModel[Dict[str, HeroData]]):
    """API response model for heroes data.

    Attributes:
        root: Dictionary mapping hero IDs to HeroData (Dict[str, HeroData])
    """

    root: Dict[str, HeroData]
