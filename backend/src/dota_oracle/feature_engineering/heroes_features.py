import pandas as pd
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.constants import DRAFT_COLS

logger = get_logger(__name__)


def create_hero_features(input_df: pd.DataFrame) -> pd.DataFrame:
    
    required_cols = DRAFT_COLS + ['match_id']
    missing_cols = [col for col in required_cols if col not in input_df.columns]
    if missing_cols:
        logger.error(f"Input DataFrame missing required columns: {missing_cols}")
        raise ValueError(f"Input DataFrame missing required columns: {missing_cols}")
    
    df_copy = input_df.copy()

    df_heroes_only = df_copy[DRAFT_COLS]
    
    # convert to type int, then aggregate series into a list using series method
    hero_picks_series = df_heroes_only.apply(lambda row: row.astype(int).tolist(), axis=1)
    
    output_df = pd.DataFrame({
        'match_id': df_copy['match_id'],
        'hero_picks': hero_picks_series
    })

    logger.info(f"Created hero pick list (simplified) for {len(output_df)} matches.")
    return output_df

    
    