import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from collections import defaultdict

# Assuming 'HeroDataTable' is the class for your hero data objects.
# from your_models import HeroDataTable


class HeroAttributeTransformer(BaseEstimator, TransformerMixin):
    """
    A feature engineering transformer that converts hero picks into a rich set
    of team-level structural features based on static hero attributes.

    It learns all possible attributes during `fit` and then creates count-based
    features during `transform`. This approach is inherently leak-free as it
    does not use the win/loss target variable.
    """

    def __init__(self):
        pass

    def fit(self, hero_data_list: list, y=None):
        """
        Learns the complete universe of categorical attributes from the hero data.
        This includes all possible roles and primary attributes.
        """
        print("Fitting HeroAttributeTransformer: Learning all possible attributes...")

        # --- Create a fast lookup map from hero_id to its data ---
        self.hero_map_ = {hero.id: hero for hero in hero_data_list}

        # --- Learn all unique categorical values ---
        all_roles = set()
        all_primary_attrs = set()

        for hero in hero_data_list:
            for role in hero.roles:
                all_roles.add(role)
            if hero.primary_attr:
                all_primary_attrs.add(hero.primary_attr)

        # Store the learned attributes, sorted for consistent column order
        self.all_roles_ = sorted(list(all_roles))
        self.all_primary_attrs_ = sorted(list(all_primary_attrs))

        print(f"Learned {len(self.all_roles_)} unique roles.")
        print(f"Learned {len(self.all_primary_attrs_)} unique primary attributes.")

        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms a DataFrame with 'hero_picks' into team-level attribute counts.
        """
        if not hasattr(self, "hero_map_"):
            raise RuntimeError("You must call .fit() before .transform()")

        print(f"Transforming {len(df)} matches into attribute features...")

        features_list = []

        # Using itertuples for a significant speedup over iterrows
        for row in df.itertuples():
            radiant_heroes = row.hero_picks[:5]
            dire_heroes = row.hero_picks[5:]

            # --- Initialize count dictionaries for this match ---
            # Using defaultdict is clean and avoids KeyError
            radiant_counts = defaultdict(int)
            dire_counts = defaultdict(int)

            # --- Process Radiant Team ---
            for hero_id in radiant_heroes:
                hero_data = self.hero_map_.get(hero_id)
                if hero_data:
                    # Count attack type
                    radiant_counts[f"attack_type_{hero_data.attack_type}"] += 1
                    # Count primary attribute
                    radiant_counts[f"attr_{hero_data.primary_attr}"] += 1
                    # Count each role
                    for role in hero_data.roles:
                        radiant_counts[f"role_{role}"] += 1

            # --- Process Dire Team ---
            for hero_id in dire_heroes:
                hero_data = self.hero_map_.get(hero_id)
                if hero_data:
                    dire_counts[f"attack_type_{hero_data.attack_type}"] += 1
                    dire_counts[f"attr_{hero_data.primary_attr}"] += 1
                    for role in hero_data.roles:
                        dire_counts[f"role_{role}"] += 1

            # --- Combine into a single record for the match ---
            match_features = {"match_id": row.match_id}

            # Add all possible features, defaulting to 0 if not present in the draft
            # This ensures all rows have the same columns
            for key in ["Melee", "Ranged"]:
                match_features[f"radiant_attack_type_{key}"] = radiant_counts[f"attack_type_{key}"]
                match_features[f"dire_attack_type_{key}"] = dire_counts[f"attack_type_{key}"]

            for attr in self.all_primary_attrs_:
                match_features[f"radiant_attr_{attr}"] = radiant_counts[f"attr_{attr}"]
                match_features[f"dire_attr_{attr}"] = dire_counts[f"attr_{attr}"]

            for role in self.all_roles_:
                match_features[f"radiant_role_{role}"] = radiant_counts[f"role_{role}"]
                match_features[f"dire_role_{role}"] = dire_counts[f"role_{role}"]

            features_list.append(match_features)

        return pd.DataFrame(features_list)


# --- EXAMPLE USAGE ---
"""

# Assume `hero_data_list` is your list of HeroDataTable objects
# Assume `hero_df` is your DataFrame with 'match_id' and 'hero_picks'

# 1. Instantiate the transformer
attribute_transformer = HeroAttributeTransformer()

# 2. Fit it on your hero data to learn all possible attributes
# attribute_transformer.fit(hero_data_list)

# 3. Transform your match data to create the final features
# hero_attribute_features_df = attribute_transformer.transform(hero_df)

# print("\n--- Final Hero Attribute Features DataFrame ---")
# print(hero_attribute_features_df.head())
# print("\nShape of the new features DataFrame:", hero_attribute_features_df.shape)
# print("\nExample columns:", hero_attribute_features_df.columns[:5].tolist(), "...")

"""
