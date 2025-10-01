from functools import reduce
import pandas as pd
from typing import Iterable, Optional, Sequence, Tuple
from sklearn.model_selection import train_test_split

def merge_features_on_match_id(
    dfs: Iterable[pd.DataFrame],
    on_key: str = "match_id"
) -> pd.DataFrame:
    """
    Merge multiple feature DataFrames on a specified key using inner joins.

    This is a robust way to combine feature sets, ensuring that only records
    present in ALL DataFrames are kept.

    Args:
        dfs: Iterable of pandas DataFrames. Each must contain the `on_key` column.
        on_key: The column name to join on, typically 'match_id'.

    Returns:
        A single DataFrame merged on the specified key.
    """
    df_list = [df for df in dfs if not df.empty]
    if not df_list:
        return pd.DataFrame()

    for i, df in enumerate(df_list):
        if on_key not in df.columns:
            raise ValueError(f"DataFrame at index {i} is missing the join key '{on_key}'")

    # use functools reduce for conciseness
    merged_df = reduce(
        lambda left, right: pd.merge(left, right, on=on_key, how="inner"),
        df_list
    )
    
    return merged_df


def create_train_test_split(
    dataframe: pd.DataFrame,
    test_size: float = 0.2,

) -> Tuple[pd.DataFrame, pd.DataFrame]:
    
    train_df, test_df = train_test_split(
        dataframe,
        test_size=test_size,
        random_state=42,
        shuffle=False  # Important: shuffle to avoid temporal leakage
    )

    return train_df, test_df


def make_train_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.3,
    random_state: int = 42,
    head: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    
    if head is not None:
        X = X.head(head)
        y = y.head(head)
        
    n_total = len(X)
    split_idx = int(n_total * (1 - test_size))

    if split_idx <= 0 or split_idx >= n_total:
        raise ValueError(
            f"Invalid split index {split_idx} calculated for test_size={test_size} "
            f"and data length={n_total}. Please check your inputs."
        )

    # The first part is for training (the "past")
    X_train = X.iloc[:split_idx]
    y_train = y.iloc[:split_idx]

    # The last part is for testing (the "future")
    X_test = X.iloc[split_idx:]
    y_test = y.iloc[split_idx:]

    return X_train, X_test, y_train, y_test
        
    
    
    
    