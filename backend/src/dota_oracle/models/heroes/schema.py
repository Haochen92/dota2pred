from pydantic import BaseModel, RootModel
from typing import Dict, List, Optional

class HeroData(BaseModel):
    
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
    
class HeroesAPIResponse(RootModel):
    root: Dict[str, HeroData]











