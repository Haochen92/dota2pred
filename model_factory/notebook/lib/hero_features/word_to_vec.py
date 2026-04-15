# In a file like lib/embedding_features.py

import pandas as pd
import numpy as np
from gensim.models import Word2Vec
from typing import List, Dict, Any


class Word2VecFeatureCreator:
    """
    A class to create team-level features from hero picks using a contrastive
    Word2Vec model.

    This class encapsulates the entire pipeline:
    1. Creating 'contrastive' sentences (e.g., ['WIN', hero1, hero2...]).
    2. Training a Word2Vec model on these sentences.
    3. Extracting learned hero embeddings.
    4. Calculating team centroids, difference vectors, and cosine similarity
       for each match.

    Follows the scikit-learn .fit() and .transform() API.
    """

    def __init__(
        self, vector_size: int = 64, window: int = 6, min_count: int = 5, sg: int = 1, workers: int = 4, **kwargs: Any
    ):
        """
        Initializes the feature creator with Word2Vec model hyperparameters.

        Args:
            vector_size: Dimensionality of the hero vectors.
            window: Maximum distance between the current and predicted word.
            min_count: Ignores all words with a total frequency lower than this.
            sg: Training algorithm: 1 for skip-gram; otherwise CBOW.
            workers: Use this many worker threads to train the model.
            **kwargs: Additional keyword arguments to pass to the Word2Vec model.
        """
        self.vector_size = vector_size
        self.window = window
        self.min_count = min_count
        self.sg = sg
        self.workers = workers
        self.kwargs = kwargs

        self.model: Word2Vec | None = None
        self.hero_embeddings: Dict[int, np.ndarray] = {}
        self.default_vector: np.ndarray = np.zeros(self.vector_size)

    @staticmethod
    def _create_contrastive_sentences(df: pd.DataFrame) -> List[List[str]]:
        """Creates sentences where team picks are preceded by WIN or LOSS."""
        sentences = []
        for _, row in df.iterrows():
            picks = row["hero_picks"]
            if row["radiant_win"]:
                sentences.append(["WIN"] + [str(h) for h in picks[:5]])
                sentences.append(["LOSS"] + [str(h) for h in picks[5:]])
            else:
                sentences.append(["LOSS"] + [str(h) for h in picks[:5]])
                sentences.append(["WIN"] + [str(h) for h in picks[5:]])
        return sentences

    def fit(self, hero_with_outcome_df: pd.DataFrame):
        """
        Trains the Word2Vec model and learns the hero embeddings.

        Args:
            hero_with_outcome_df: DataFrame containing 'hero_picks' (list of ints)
                                  and 'radiant_win' (bool/int) for each match.

        Returns:
            self: The fitted instance of the class.
        """
        print("Step 1/3: Creating contrastive training sentences...")
        sentences = self._create_contrastive_sentences(hero_with_outcome_df)

        print("Step 2/3: Training contrastive Word2Vec model...")
        self.model = Word2Vec(
            sentences=sentences,
            vector_size=self.vector_size,
            window=self.window,
            min_count=self.min_count,
            sg=self.sg,
            workers=self.workers,
            **self.kwargs,
        )

        print("Step 3/3: Extracting final hero embedding map...")
        self.hero_embeddings = {}
        for hero_id_str in self.model.wv.index_to_key:
            if hero_id_str not in ["WIN", "LOSS"]:
                self.hero_embeddings[int(hero_id_str)] = self.model.wv[hero_id_str]

        print("Fit complete. Embeddings for", len(self.hero_embeddings), "heroes learned.")
        return self

    def transform(self, hero_df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates features by concatenating all 10 hero vectors into a single feature row.
        """
        if self.model is None or not self.hero_embeddings:
            raise RuntimeError("You must call .fit() before using .transform().")

        print("Calculating features using vector concatenation...")

        # We will build a list of dictionaries, which is efficient for creating a DataFrame
        feature_rows = []

        for row in hero_df.itertuples(index=False):
            current_match_features = {"match_id": row.match_id}
            picks = row.hero_picks

            # Get vectors for Radiant heroes
            radiant_vecs = [self.hero_embeddings.get(h, self.default_vector) for h in picks[:5]]

            # Get vectors for Dire heroes
            dire_vecs = [self.hero_embeddings.get(h, self.default_vector) for h in picks[5:]]

            # Flatten and add Radiant hero features
            for i, vec in enumerate(radiant_vecs):
                for j, val in enumerate(vec):
                    current_match_features[f"radiant_hero_{i+1}_dim_{j}"] = val

            # Flatten and add Dire hero features
            for i, vec in enumerate(dire_vecs):
                for j, val in enumerate(vec):
                    current_match_features[f"dire_hero_{i+1}_dim_{j}"] = val

            feature_rows.append(current_match_features)

        # Create the final DataFrame
        final_df = pd.DataFrame(feature_rows)

        print("Transformation complete. Final shape:", final_df.shape)
        return final_df

    def fit_transform(self, hero_with_outcome_df: pd.DataFrame) -> pd.DataFrame:
        """A convenience method to fit and then transform the same data."""
        self.fit(hero_with_outcome_df)
        return self.transform(hero_with_outcome_df)
