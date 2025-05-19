import pandas as pd
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.data_repository.heroes_repository import HeroesRepository
from typing import List, Dict
from dota_oracle.constants import DRAFT_COLS, PLAYER_COLS, TEAM_COL, TIME_COL, UUID_COL

logger = get_logger(__name__)

class FeaturesPreprocessor:
    def __init__(self, hero_repository: HeroesRepository):
        self.hero_repo = hero_repository
    

    async def preprocess_live_match_data(self, input_df: pd.DataFrame) -> pd.DataFrame:
        '''
            Preprocess dataframe of a single live match game
        '''
        if isinstance(input_df, pd.DataFrame):
            # Create a smaller copy 
            df = input_df.copy()
        else:
            raise TypeError("Input must be pandas DataFrame")
        hero_map = await self.hero_repo.get_hero_id_map()
        # Convert Unix time to datetime format
        df = self.map_hero_ids_to_names(df, DRAFT_COLS, hero_map)
        
        return df
        
    async def preprocess_batch_match_data(self, input_df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocesses a batch DataFrame: selects columns, handles NaNs,
        removes duplicates, converts time, maps hero IDs, and sorts.
        """
        if not isinstance(input_df, pd.DataFrame):
            raise TypeError("Input must be pandas DataFrame")

        if input_df.empty:
            logger.warning("Received empty DataFrame for batch preprocessing.")
            return input_df 

        logger.info(f"Starting batch preprocessing for {len(input_df)} rows...")

        # 1. --- Column Existence Check (BEFORE selection) ---
        required_cols = DRAFT_COLS + PLAYER_COLS + TEAM_COL + [TIME_COL, UUID_COL] 
        missing_cols = [col for col in required_cols if col not in input_df.columns]
        if missing_cols:
            logger.error(f"Input DataFrame missing required columns: {missing_cols}. Cannot preprocess.")
            raise ValueError(f"Missing required columns: {missing_cols}")
        # -----------------------------------------------------

        # 2. Select columns and copy
        df = input_df[required_cols].copy()
        logger.debug(f"Selected {len(required_cols)} columns.")

        # 3. Handle Duplicates
        initial_rows = len(df)
        df = df.drop_duplicates(subset=[UUID_COL], keep='first')
        removed_dupes = initial_rows - len(df)
        if removed_dupes > 0:
            logger.info(f"Removing {removed_dupes} duplicate matches based on {UUID_COL}.")
        if df.empty:
            logger.warning("DataFrame empty after removing duplicates.")
            return df

        # 4. Apply Common Transformations
        hero_map = await self.hero_repo.get_hero_id_map()
        df = self.map_hero_ids_to_names(df, DRAFT_COLS, hero_map)

        # 5. Handle Missing Values (after potential coercion/mapping)
        initial_rows = len(df)
        df = df.dropna() 
        removed_nan = initial_rows - len(df)
        if removed_nan > 0:
            logger.info(f"Removed {removed_nan} rows with missing values after transformations.")
        if df.empty:
            logger.warning("DataFrame empty after removing NaNs.")
            return df

        # 6. Sort
        df = df.sort_values(by=TIME_COL).reset_index(drop=True)
        logger.debug("Sorted DataFrame by time.")

        logger.info(f"Finished batch preprocessing. {len(df)} rows remaining.")
        return df


    def map_hero_ids_to_names(self, 
        df: pd.DataFrame,
        draft_cols: List[str],
        hero_map: Dict[int, str]
    ):
        for col in draft_cols:
            numeric_col = pd.to_numeric(df[col], errors='coerce')
            df[col] = numeric_col.map(hero_map).fillna("unknown_hero")
            
        return df




