"""
Stacking experiment on PUBLIC matches:
  hero win rate features + GNN embeddings → LightGBM

Compares:
  A) Hero WR features only (baseline)
  B) GNN embeddings only (PCA-32)
  C) GNN embeddings only (raw 512)
  D) Hero WR + GNN PCA-32 (stacked)
  E) Hero WR + GNN raw-512 (stacked)
"""
import sys, json, gc
from types import SimpleNamespace
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MultiLabelBinarizer
from sklearn.decomposition import PCA
from torch_geometric.nn import RGCNConv
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch.utils.data import Dataset
import lightgbm as lgb

sys.path.insert(0, ".")
from lib.data_management import load_pro_matches_parquet
from dota_oracle_common.models.heroes import HeroData
from dota_oracle_pipeline.feature_engineering.batch.hero_wr_features.decay import (
    BatchHeroWinrateDecayFeatureGenerator,
)


# =============================================================================
# GNN MODEL (must match training architecture)
# =============================================================================

def build_relational_edges():
    r, d = list(range(5)), list(range(5, 10))
    edges, types = [], []
    for team in (r, d):
        for i in team:
            for j in team:
                if i != j: edges.append((i, j)); types.append(0)
    for i in r:
        for j in d:
            edges.extend([(i, j), (j, i)]); types.extend([1, 1])
    for i in range(10):
        edges.append((i, i)); types.append(2)
    return torch.tensor(edges, dtype=torch.long).t().contiguous(), torch.tensor(types, dtype=torch.long)

EDGE_INDEX, EDGE_TYPE = build_relational_edges()


class HybridGCN(nn.Module):
    def __init__(self, feature_dim, num_heroes, embedding_dim, num_relations, hidden_dim, dropout_rate=0.2):
        super().__init__()
        self.hero_embedding = nn.Embedding(num_heroes, embedding_dim)
        combined_input_dim = feature_dim + embedding_dim
        self.conv1 = RGCNConv(combined_input_dim, hidden_dim, num_relations)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.conv2 = RGCNConv(hidden_dim, hidden_dim, num_relations)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.output_layer = nn.Sequential(
            nn.Linear(4 * hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(p=dropout_rate),
            nn.Linear(hidden_dim, 1),
        )
        self.dropout = nn.Dropout(p=dropout_rate)

    def forward(self, data):
        x = data.x
        hero_idx = data.hero_indices
        emb = self.hero_embedding(hero_idx)
        x = torch.cat([x, emb], dim=-1)
        x = self.bn1(self.conv1(x, data.edge_index, data.edge_type)).relu()
        x = self.dropout(x)
        x = self.bn2(self.conv2(x, data.edge_index, data.edge_type)).relu()
        x = self.dropout(x)
        num_graphs = data.batch.max().item() + 1
        x_per_graph = x.view(num_graphs, 10, -1)
        radiant_pool = x_per_graph[:, :5, :].mean(dim=1)
        dire_pool = x_per_graph[:, 5:, :].mean(dim=1)
        diff = radiant_pool - dire_pool
        interaction = radiant_pool * dire_pool
        return torch.cat([radiant_pool, dire_pool, diff, interaction], dim=1)


class HybridDraftDataset(Dataset):
    def __init__(self, radiant_ids, dire_ids, hero_feature_matrix):
        self.radiant_ids = radiant_ids
        self.dire_ids = dire_ids
        self.hero_features = hero_feature_matrix

    def __len__(self):
        return len(self.radiant_ids)

    def __getitem__(self, idx):
        hero_indices_np = np.concatenate([self.radiant_ids[idx], self.dire_ids[idx]])
        draft_features = self.hero_features[hero_indices_np]
        g = Data(
            x=draft_features,
            hero_indices=torch.from_numpy(hero_indices_np).long(),
            edge_index=EDGE_INDEX, edge_type=EDGE_TYPE,
        )
        g.num_nodes = 10
        return g


# =============================================================================
# HELPERS
# =============================================================================

def create_hero_feature_matrix(hero_objects, id_to_idx_map):
    hero_data_dict = {h.id: h for h in hero_objects}
    num_heroes = len(id_to_idx_map)
    numerical_cols = [
        'agi_gain', 'base_agi', 'int_gain', 'base_int', 'str_gain', 'base_str',
        'attack_rate', 'attack_range', 'attack_point', 'projectile_speed',
        'base_armor', 'base_mana', 'base_mana_regen', 'base_health', 'base_health_regen'
    ]
    num_list = [
        [getattr(hero_data_dict[h_id], col) or 0 for col in numerical_cols]
        for h_id in id_to_idx_map.keys()
    ]
    scaler = StandardScaler()
    scaled = scaler.fit_transform(num_list)
    attr_oh = pd.get_dummies([hero_data_dict[h].primary_attr for h in id_to_idx_map], prefix='attr').values
    atk_oh = pd.get_dummies([hero_data_dict[h].attack_type for h in id_to_idx_map], prefix='atk').values
    mlb = MultiLabelBinarizer()
    roles = mlb.fit_transform([hero_data_dict[h].roles for h in id_to_idx_map])
    combined = np.concatenate([scaled, attr_oh, atk_oh, roles], axis=1)
    final = np.zeros((num_heroes, combined.shape[1]))
    for hero_id, hero_idx in id_to_idx_map.items():
        original_pos = list(id_to_idx_map.keys()).index(hero_id)
        final[hero_idx] = combined[original_pos]
    return torch.tensor(final, dtype=torch.float)


def df_to_match_like(df):
    """Convert parquet DataFrame rows to SimpleNamespace match-like objects."""
    rad_cols = [f"slot_{i}_hero_id" for i in range(5)]
    dir_cols = [f"slot_{i}_hero_id" for i in range(128, 133)]
    records = []
    for _, row in df.iterrows():
        obj = SimpleNamespace(
            match_id=int(row["match_id"]),
            start_time=row["start_time"],
            outcome=SimpleNamespace(radiant_win=bool(row["radiant_win"])),
        )
        for c in rad_cols + dir_cols:
            setattr(obj, c, int(row[c]))
        records.append(obj)
    return records


def extract_gnn_embeddings(model, radiant_ids, dire_ids, hero_features, device, batch_size=2048):
    model.eval()
    dataset = HybridDraftDataset(radiant_ids, dire_ids, hero_features)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    all_emb = []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            emb = model(batch)
            all_emb.append(emb.cpu().numpy())
    return np.concatenate(all_emb, axis=0)


def prepare_draft_arrays(df, id_to_idx_map):
    rad_cols = [f"slot_{i}_hero_id" for i in range(5)]
    dir_cols = [f"slot_{i}_hero_id" for i in range(128, 133)]
    sub = df.dropna(subset=rad_cols + dir_cols).copy().reset_index(drop=True)
    r_raw = sub[rad_cols].astype(np.int64).to_numpy()
    d_raw = sub[dir_cols].astype(np.int64).to_numpy()
    known = set(id_to_idx_map.keys())
    all_h = np.concatenate([r_raw, d_raw], axis=1)
    valid = np.array([all(int(h) in known for h in row) for row in all_h])
    dropped = (~valid).sum()
    if dropped > 0:
        print(f"  Dropping {dropped} matches with unknown heroes")
    sub = sub[valid].reset_index(drop=True)
    r_raw, d_raw = r_raw[valid], d_raw[valid]
    mapper = np.vectorize(id_to_idx_map.get, otypes=[np.int64])
    return mapper(r_raw), mapper(d_raw), sub["radiant_win"].astype(int).to_numpy(), sub["match_id"].to_numpy()


# =============================================================================
# MAIN
# =============================================================================

def main():
    device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
    print(f"Device: {device}")

    # --- Step 1: Load data ---
    print("\n=== Step 1: Load public matches ===")
    pub_df = load_pro_matches_parquet("../data/public_matches_dataset.parquet")
    print(f"Loaded {len(pub_df)} public matches")

    # Temporal train/test split (same as GNN training)
    train_df, test_df = train_test_split(pub_df, test_size=0.2, shuffle=False, random_state=42)
    print(f"Train: {len(train_df)}, Test: {len(test_df)}")

    # --- Step 2: Compute hero win rate features ---
    print("\n=== Step 2: Computing hero win rate features ===")
    print("Converting to match-like objects (this takes a minute)...")
    all_match_like = df_to_match_like(pub_df)

    gen = BatchHeroWinrateDecayFeatureGenerator()
    print("Generating hero decay features...")
    hero_wide, _ = gen.generate(
        all_match_like, prior_mean=0.5, prior_count=50, half_life_days=45
    )
    df_hero = pd.DataFrame([r.model_dump() for r in hero_wide])

    rad_wr_cols = [f"hero_{i}_win_rate" for i in range(5)]
    dir_wr_cols = [f"hero_{i}_win_rate" for i in range(128, 133)]
    df_hero["radiant_avg_hero_wr"] = df_hero[rad_wr_cols].mean(axis=1)
    df_hero["dire_avg_hero_wr"] = df_hero[dir_wr_cols].mean(axis=1)
    df_hero["radiant_dire_hero_wr_diff"] = df_hero["radiant_avg_hero_wr"] - df_hero["dire_avg_hero_wr"]

    # Also keep per-hero WRs as granular features (10 features)
    hero_feature_cols = rad_wr_cols + dir_wr_cols + ["radiant_dire_hero_wr_diff"]
    df_hero_features = df_hero[["match_id"] + hero_feature_cols].copy()
    print(f"Hero features: {len(hero_feature_cols)} columns")

    del all_match_like, hero_wide
    gc.collect()

    # --- Step 3: Load GNN and extract embeddings ---
    print("\n=== Step 3: Loading GNN and extracting embeddings ===")
    with Path("../data/heroes_data.jsonl").open("r") as f:
        heroes = json.load(f)
    hero_objects = [HeroData.model_validate(h) for h in heroes]

    # Rebuild id_to_idx from public training data (same as GNN training)
    rad_cols = [f"slot_{i}_hero_id" for i in range(5)]
    dir_cols = [f"slot_{i}_hero_id" for i in range(128, 133)]
    sub = train_df.dropna(subset=rad_cols + dir_cols).copy()
    r_raw = sub[rad_cols].astype(np.int64).to_numpy()
    d_raw = sub[dir_cols].astype(np.int64).to_numpy()
    all_ids = np.concatenate([r_raw.ravel(), d_raw.ravel()])
    uniq = np.unique(all_ids)
    id_to_idx = {int(h): i for i, h in enumerate(uniq)}
    num_heroes = len(id_to_idx)
    print(f"id_to_idx: {num_heroes} heroes")

    hero_feat_matrix = create_hero_feature_matrix(hero_objects, id_to_idx)
    feature_dim = hero_feat_matrix.shape[1]

    model = HybridGCN(
        feature_dim=feature_dim, num_heroes=num_heroes,
        embedding_dim=64, num_relations=3, hidden_dim=128, dropout_rate=0.2,
    ).to(device)
    model.load_state_dict(torch.load("best_hybrid_gcn.pth", weights_only=True, map_location=device))
    model.eval()
    print("HybridGCN loaded")

    # Extract for train
    print("Extracting train embeddings...")
    r_train, d_train, y_train, mids_train = prepare_draft_arrays(train_df, id_to_idx)
    emb_train = extract_gnn_embeddings(model, r_train, d_train, hero_feat_matrix, device)
    print(f"  Train embeddings: {emb_train.shape}")

    # Extract for test
    print("Extracting test embeddings...")
    r_test, d_test, y_test, mids_test = prepare_draft_arrays(test_df, id_to_idx)
    emb_test = extract_gnn_embeddings(model, r_test, d_test, hero_feat_matrix, device)
    print(f"  Test embeddings: {emb_test.shape}")

    # --- Step 4: Merge hero WR features with GNN embeddings ---
    print("\n=== Step 4: Merging features ===")

    # Train
    train_emb_df = pd.DataFrame(emb_train, columns=[f"gnn_{i}" for i in range(emb_train.shape[1])])
    train_emb_df["match_id"] = mids_train
    train_emb_df["y"] = y_train
    train_merged = train_emb_df.merge(df_hero_features, on="match_id", how="inner")

    # Test
    test_emb_df = pd.DataFrame(emb_test, columns=[f"gnn_{i}" for i in range(emb_test.shape[1])])
    test_emb_df["match_id"] = mids_test
    test_emb_df["y"] = y_test
    test_merged = test_emb_df.merge(df_hero_features, on="match_id", how="inner")

    print(f"Train merged: {len(train_merged)}, Test merged: {len(test_merged)}")

    y_train_m = train_merged["y"].to_numpy()
    y_test_m = test_merged["y"].to_numpy()

    gnn_cols = [c for c in train_merged.columns if c.startswith("gnn_")]

    # --- Step 5: PCA on GNN embeddings ---
    print("\n=== Step 5: PCA on GNN embeddings ===")
    pca = PCA(n_components=32)
    gnn_train_pca = pca.fit_transform(train_merged[gnn_cols].to_numpy())
    gnn_test_pca = pca.transform(test_merged[gnn_cols].to_numpy())
    print(f"PCA-32 explains {pca.explained_variance_ratio_.sum():.1%} of GNN variance")

    # --- Step 6: Train LightGBM on different feature sets ---
    print("\n=== Step 6: Training LightGBM models ===")
    lgb_params = {
        "objective": "binary", "metric": "binary_logloss",
        "verbosity": -1, "n_estimators": 300, "learning_rate": 0.05,
        "num_leaves": 31, "min_child_samples": 20,
    }

    results = {}

    # A) Hero WR diff only (1 feature, matches pub_matches_model baseline)
    print("\n--- A) Hero WR diff only (1 feature) ---")
    X_tr_a = train_merged[["radiant_dire_hero_wr_diff"]].to_numpy()
    X_te_a = test_merged[["radiant_dire_hero_wr_diff"]].to_numpy()
    m_a = lgb.LGBMClassifier(**lgb_params)
    m_a.fit(X_tr_a, y_train_m)
    acc_a = (m_a.predict(X_te_a) == y_test_m).mean()
    results["Hero WR diff (1 feat)"] = acc_a
    print(f"  Test Accuracy: {acc_a:.4f}")

    # B) Granular hero WRs (11 features: 10 per-hero + 1 diff)
    print("\n--- B) Granular hero WRs (11 features) ---")
    X_tr_b = train_merged[hero_feature_cols].to_numpy()
    X_te_b = test_merged[hero_feature_cols].to_numpy()
    m_b = lgb.LGBMClassifier(**lgb_params)
    m_b.fit(X_tr_b, y_train_m)
    acc_b = (m_b.predict(X_te_b) == y_test_m).mean()
    results["Granular hero WRs (11 feat)"] = acc_b
    print(f"  Test Accuracy: {acc_b:.4f}")

    # C) GNN embeddings only (PCA-32)
    print("\n--- C) GNN embeddings only (PCA-32) ---")
    m_c = lgb.LGBMClassifier(**lgb_params)
    m_c.fit(gnn_train_pca, y_train_m)
    acc_c = (m_c.predict(gnn_test_pca) == y_test_m).mean()
    results["GNN only (PCA-32)"] = acc_c
    print(f"  Test Accuracy: {acc_c:.4f}")

    # D) GNN raw 512
    print("\n--- D) GNN embeddings only (raw 512) ---")
    X_tr_d = train_merged[gnn_cols].to_numpy()
    X_te_d = test_merged[gnn_cols].to_numpy()
    m_d = lgb.LGBMClassifier(**lgb_params)
    m_d.fit(X_tr_d, y_train_m)
    acc_d = (m_d.predict(X_te_d) == y_test_m).mean()
    results["GNN only (raw-512)"] = acc_d
    print(f"  Test Accuracy: {acc_d:.4f}")

    # E) Hero WR diff + GNN PCA-32
    print("\n--- E) Hero WR diff + GNN PCA-32 (stacked) ---")
    X_tr_e = np.concatenate([X_tr_a, gnn_train_pca], axis=1)
    X_te_e = np.concatenate([X_te_a, gnn_test_pca], axis=1)
    m_e = lgb.LGBMClassifier(**lgb_params)
    m_e.fit(X_tr_e, y_train_m)
    acc_e = (m_e.predict(X_te_e) == y_test_m).mean()
    results["Hero WR + GNN PCA-32"] = acc_e
    print(f"  Test Accuracy: {acc_e:.4f}")

    # F) Granular hero WRs + GNN PCA-32
    print("\n--- F) Granular hero WRs + GNN PCA-32 (stacked) ---")
    X_tr_f = np.concatenate([X_tr_b, gnn_train_pca], axis=1)
    X_te_f = np.concatenate([X_te_b, gnn_test_pca], axis=1)
    m_f = lgb.LGBMClassifier(**lgb_params)
    m_f.fit(X_tr_f, y_train_m)
    acc_f = (m_f.predict(X_te_f) == y_test_m).mean()
    results["Granular WRs + GNN PCA-32"] = acc_f
    print(f"  Test Accuracy: {acc_f:.4f}")

    # G) Granular hero WRs + GNN raw 512
    print("\n--- G) Granular hero WRs + GNN raw 512 (stacked) ---")
    X_tr_g = np.concatenate([X_tr_b, X_tr_d], axis=1)
    X_te_g = np.concatenate([X_te_b, X_te_d], axis=1)
    m_g = lgb.LGBMClassifier(**lgb_params)
    m_g.fit(X_tr_g, y_train_m)
    acc_g = (m_g.predict(X_te_g) == y_test_m).mean()
    results["Granular WRs + GNN raw-512"] = acc_g
    print(f"  Test Accuracy: {acc_g:.4f}")

    # --- Summary ---
    baseline_acc = acc_b  # granular hero WRs
    print("\n" + "=" * 65)
    print("RESULTS SUMMARY (sorted by accuracy)")
    print("=" * 65)
    for name, acc in sorted(results.items(), key=lambda x: -x[1]):
        delta = acc - baseline_acc
        marker = " (baseline)" if name == "Granular hero WRs (11 feat)" else f" ({delta:+.2%})"
        print(f"  {acc:.4f}  {name}{marker}")
    print("=" * 65)

    # Feature importance for best stacked model
    print("\nTop 15 feature importances (Granular WRs + GNN PCA-32):")
    feat_names = hero_feature_cols + [f"gnn_pca_{i}" for i in range(32)]
    importances = m_f.feature_importances_
    for name, imp in sorted(zip(feat_names, importances), key=lambda x: -x[1])[:15]:
        print(f"  {imp:4d}  {name}")


if __name__ == "__main__":
    main()
