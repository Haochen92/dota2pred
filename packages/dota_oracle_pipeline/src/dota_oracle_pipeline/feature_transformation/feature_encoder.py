from sklearn.preprocessing import MultiLabelBinarizer
import pandas as pd
from scipy import sparse
from typing import Dict
from dota_oracle_common.models.api.schema import PublicMatchPredictionRequest


class FeatureEncoder:
    """
    A stateful service for encoding hero features for model inference.

    This class is designed to be initialized ONCE at application startup with a
    complete hero map. It pre-fits a MultiLabelBinarizer, ensuring that all
    subsequent encoding operations are fast, efficient, and consistent.

    Attributes:
        hero_map (Dict[int, str]): A mapping of hero IDs to hero names.
        encoder (MultiLabelBinarizer): A pre-fitted encoder ready for transformations.
    """

    def __init__(self, hero_map: Dict[int, str]):
        """
        Initializes the FeatureEncoder and its internal encoder.

        Args:
            hero_map: The complete dictionary mapping hero IDs to hero names.
                      The key order of this map dictates the feature order.
        """
        if not hero_map:
            raise ValueError("hero_map cannot be empty.")

        self.hero_map = hero_map
        self.encoder = self._initialize_encoder()

    def _initialize_encoder(self) -> MultiLabelBinarizer:
        """
        Creates and fits the MultiLabelBinarizer based on the hero map.
        This internal method is called only once during initialization.
        """
        # We will standardize on using hero IDs for the encoder's classes,
        # as they are more robust than names.
        all_hero_ids_in_order = list(self.hero_map.keys())

        mlb = MultiLabelBinarizer(classes=all_hero_ids_in_order)
        # "Fit" the encoder on an empty list; providing `classes` is sufficient.
        mlb.fit([])

        return mlb

    def transform_batch(self, hero_features: pd.DataFrame) -> pd.DataFrame:
        """
        Encodes a batch of hero picks from a DataFrame.

        This method is designed for batch processing, such as training or
        evaluating the model on historical data. It expects a DataFrame
        with a 'hero_picks' column containing lists of hero IDs.

        Args:
            hero_features: A DataFrame containing at least a 'hero_picks'
                           column (list of hero IDs) and a 'match_id' column.

        Returns:
            A new DataFrame containing the one-hot encoded hero features,
            the original index, and the 'match_id' column.
        """
        if hero_features.empty:
            raise ValueError("Input DataFrame is empty.")
        if "hero_picks" not in hero_features.columns:
            raise ValueError("Input DataFrame is missing the required 'hero_picks' column.")

        # Use the pre-fitted encoder to transform the hero ID lists.
        # The input to `transform` is a Series of lists, which is the correct format.
        hero_matrix = self.encoder.transform(hero_features["hero_picks"])

        # Convert to sparse matrix if it isn't already (MultiLabelBinarizer may return dense for small data)
        if not sparse.issparse(hero_matrix):
            hero_matrix = sparse.csr_matrix(hero_matrix)

        # Create the final sparse DataFrame.
        # The column names should be hero names, not IDs, to match model expectations
        hero_name_columns = [self.hero_map[hero_id] for hero_id in self.encoder.classes_]
        features = pd.DataFrame.sparse.from_spmatrix(
            data=hero_matrix,
            columns=hero_name_columns,
            index=hero_features.index,  # Preserve the original index for alignment
        )

        # Re-attach the match_id for easy reference
        if "match_id" in hero_features.columns:
            features = features.assign(match_id=hero_features["match_id"])

        return features

    def transform_single_request(self, public_request: PublicMatchPredictionRequest) -> pd.DataFrame:
        """
        Encodes hero picks from a single API request for real-time inference.

        This high-performance method is designed for the API request/response
        cycle. It takes a validated Pydantic model and quickly produces a
        single-row feature DataFrame.

        Args:
            public_request: A Pydantic model instance containing the 10 picked hero IDs.

        Returns:
            A single-row pandas DataFrame with binary columns for each hero.
        """
        all_picked_ids = [
            public_request.radiant_hero_id_1,
            public_request.radiant_hero_id_2,
            public_request.radiant_hero_id_3,
            public_request.radiant_hero_id_4,
            public_request.radiant_hero_id_5,
            public_request.dire_hero_id_1,
            public_request.dire_hero_id_2,
            public_request.dire_hero_id_3,
            public_request.dire_hero_id_4,
            public_request.dire_hero_id_5,
        ]

        # Use the pre-fitted encoder. The input must be a list of lists.
        binary_vector = self.encoder.transform([all_picked_ids])

        # Convert to sparse matrix if it isn't already (MultiLabelBinarizer may return dense for small data)
        if not sparse.issparse(binary_vector):
            binary_vector = sparse.csr_matrix(binary_vector)

        # Create the final single-row DataFrame.
        # Use hero names as column names to match model expectations
        hero_name_columns = [self.hero_map[hero_id] for hero_id in self.encoder.classes_]
        features = pd.DataFrame.sparse.from_spmatrix(data=binary_vector, columns=hero_name_columns, index=pd.Index([0]))

        return features


def create_binary_hero_features_mvp(public_request: Dict[str, int], hero_map: Dict[int, str]) -> pd.DataFrame:
    """
    (MVP VERSION) Encodes hero picks into a binary feature vector.

    !! WARNING: This is an inefficient MVP implementation. !!
    It creates and fits a new MultiLabelBinarizer on every single call,
    which is computationally expensive and not suitable for a production
    environment. It should be refactored to use a pre-fitted encoder
    for production use.

    Args:
        public_request: A dictionary representing the JSON body of the
                        prediction request (e.g., from request.json()).
        hero_map: A complete mapping of hero IDs to hero names. The key
                  order of this dictionary dictates the feature order.

    Returns:
        A single-row pandas DataFrame with binary columns for each hero,
        in the order specified by the hero_map.
    """
    try:
        all_picked_ids = [
            public_request["radiant_hero_id_1"],
            public_request["radiant_hero_id_2"],
            public_request["radiant_hero_id_3"],
            public_request["radiant_hero_id_4"],
            public_request["radiant_hero_id_5"],
            public_request["dire_hero_id_1"],
            public_request["dire_hero_id_2"],
            public_request["dire_hero_id_3"],
            public_request["dire_hero_id_4"],
            public_request["dire_hero_id_5"],
        ]
    except KeyError as e:
        raise ValueError(f"Missing required hero ID in request: {e}") from e

    # 2. Define the canonical order of all heroes from the hero_map.
    all_hero_ids_in_order = list(hero_map.keys())

    #    Create and fit a brand new encoder on every function call.
    mlb = MultiLabelBinarizer(classes=all_hero_ids_in_order)

    # Use fit_transform on the current request's data.
    binary_vector = mlb.fit_transform([all_picked_ids])

    # 4. Create the final DataFrame. The column order is guaranteed
    #    by the `classes` parameter we passed to the encoder.
    features = pd.DataFrame.sparse.from_spmatrix(data=binary_vector, columns=mlb.classes_, index=pd.Index([0]))

    return features
