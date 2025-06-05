from dota_oracle.utils.set_logging import get_logger
from dota_oracle.constants import DRAFT_COLS
from dota_oracle.models.match import MatchTable
from dota_oracle.models.features import HeroFeaturesTable
from typing import List


logger = get_logger(__name__)


def create_hero_features(match_instances: List[MatchTable]) -> List[HeroFeaturesTable]:
    
    output_hero_features_list: List[HeroFeaturesTable] = []
    
    for instance in match_instances:
        heroes_list = []
        for col_name in DRAFT_COLS:
            hero_name = getattr(instance, col_name)
            heroes_list.append(hero_name) 
            
        hero_feature = HeroFeaturesTable(
            match_id=instance.match_id,
            hero_picks=heroes_list
        )
        output_hero_features_list.append(hero_feature)
        
        
    logger.info(f"Created {len(output_hero_features_list)} hero features")
    return output_hero_features_list

    
    