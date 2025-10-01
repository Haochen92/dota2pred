from sentence_transformers import SentenceTransformer
from sklearn.base import BaseEstimator, TransformerMixin
import pandas as pd

class DraftEmbeddingTransformer(BaseEstimator, TransformerMixin):
    """
    Transforms hero drafts into dense vector embeddings using a pre-trained
    Sentence Transformer model.

    Crucially, it sorts the hero IDs before creating the "sentence" to ensure
    the embedding is order-invariant, correctly modeling the draft as a set
    of heroes rather than an ordered sequence.
    """
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model_ = SentenceTransformer(self.model_name)

    def fit(self, X, y=None):
        return self # No fitting required

    def _prepare_sentences(self, df: pd.DataFrame) -> tuple[list[str], list[str]]:
        """Converts hero pick lists into sorted, space-separated strings."""
        
        def create_sorted_sentence(picks):
            sorted_picks = sorted(picks)
            return ' '.join([f"hero_{h}" for h in sorted_picks])

        radiant_sentences = df['hero_picks'].apply(lambda p: create_sorted_sentence(p[:5])).tolist()
        dire_sentences = df['hero_picks'].apply(lambda p: create_sorted_sentence(p[5:])).tolist()
        
        return radiant_sentences, dire_sentences

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        radiant_sentences, dire_sentences = self._prepare_sentences(df)
        
        print(f"Encoding {len(radiant_sentences)} Radiant and Dire drafts...")
        radiant_embeddings = self.model_.encode(radiant_sentences, show_progress_bar=True)
        dire_embeddings = self.model_.encode(dire_sentences, show_progress_bar=True)
        
        # Create relational features
        diff_embeddings = radiant_embeddings - dire_embeddings
        
        # Create DataFrames
        diff_cols = [f'draft_emb_diff_{i}' for i in range(diff_embeddings.shape[1])]
        diff_df = pd.DataFrame(diff_embeddings, columns=diff_cols)
        
        final_df = pd.concat([
            df[['match_id']].reset_index(drop=True),
            diff_df
        ], axis=1)
        
        return final_df
    
# Example usage:
'''
# 1. Instantiate the transformer
draft_embedder = DraftEmbeddingTransformer()

# 2. Generate features for train and test sets
#    (No fitting needed, so we can do it in one pass and split, or two separate calls)

nlp_features_train = draft_embedder.transform(hero_with_outcome_df_train)
nlp_features_test = draft_embedder.transform(hero_with_outcome_df_test)
'''

