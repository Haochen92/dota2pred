from sklearn.preprocessing import MultiLabelBinarizer
import pandas as pd
from scipy import sparse

from typing import Dict

class FeatureEncoder:
    @staticmethod
    def encode_hero_features(hero_features: pd.DataFrame, hero_map: Dict[int, str]) -> pd.DataFrame:
    
        if hero_features.empty:
            raise ValueError("Input dataframe is empty")
        
        if 'hero_picks' not in hero_features.columns:
            raise ValueError("missing column hero_picks")
        
        hero_classes = hero_map.values()
        
        # for some reason mlb requires explicit conversion of view object to list
        mlb = MultiLabelBinarizer(classes=list(hero_classes)) 
        
        hero_matrix = mlb.fit_transform(hero_features['hero_picks'])
        hero_matrix_sparse = sparse.csr_matrix(hero_matrix)  # convert to sparse matrix
        
        features = pd.DataFrame.sparse.from_spmatrix(
            data=hero_matrix_sparse,
            columns=mlb.classes_,
            index=hero_features.index
        )
        
        features = features.assign(match_id=hero_features['match_id'])
        return features

