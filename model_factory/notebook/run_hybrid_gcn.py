"""Run just the HybridGCN experiment (experiment 3) with the NaN fix."""
import sys, json, gc
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MultiLabelBinarizer
from torch.utils.data import Dataset, random_split
from torch_geometric.nn import RGCNConv
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

sys.path.insert(0, ".")
from lib.data_management import load_pro_matches_parquet
from dota_oracle_common.models.heroes import HeroData


def get_default_device():
    if torch.cuda.is_available():
        return torch.device('cuda')
    elif torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


def create_hero_feature_matrix(hero_objects, id_to_idx_map):
    hero_data_dict = {h.id: h for h in hero_objects}
    num_heroes = len(id_to_idx_map)

    numerical_cols = [
        'agi_gain', 'base_agi', 'int_gain', 'base_int', 'str_gain', 'base_str',
        'attack_rate', 'attack_range', 'attack_point', 'projectile_speed',
        'base_armor', 'base_mana', 'base_mana_regen', 'base_health', 'base_health_regen'
    ]
    numerical_features_list = [
        [getattr(hero_data_dict[h_id], col) or 0 for col in numerical_cols]
        for h_id in id_to_idx_map.keys()
    ]
    scaler = StandardScaler()
    numerical_features_scaled = scaler.fit_transform(numerical_features_list)

    attr_one_hot = pd.get_dummies(
        [hero_data_dict[h_id].primary_attr for h_id in id_to_idx_map.keys()], prefix='attr'
    ).values
    attack_type_one_hot = pd.get_dummies(
        [hero_data_dict[h_id].attack_type for h_id in id_to_idx_map.keys()], prefix='atk'
    ).values

    all_roles = [hero_data_dict[h_id].roles for h_id in id_to_idx_map.keys()]
    mlb = MultiLabelBinarizer()
    roles_multi_hot = mlb.fit_transform(all_roles)

    combined = np.concatenate([
        numerical_features_scaled, attr_one_hot, attack_type_one_hot, roles_multi_hot
    ], axis=1)

    feature_dim = combined.shape[1]
    print(f"Created hero feature matrix: [{num_heroes}, {feature_dim}]")
    assert not np.isnan(combined).any(), "NaN in feature matrix!"

    final = np.zeros((num_heroes, feature_dim))
    for hero_id, hero_idx in id_to_idx_map.items():
        original_pos = list(id_to_idx_map.keys()).index(hero_id)
        final[hero_idx] = combined[original_pos]

    return torch.tensor(final, dtype=torch.float)


def prepare_draft_arrays(df, id_to_idx_map=None):
    rad_cols = [f"slot_{i}_hero_id" for i in range(5)]
    dir_cols = [f"slot_{i}_hero_id" for i in range(128, 133)]
    sub = df.dropna(subset=rad_cols + dir_cols).copy().reset_index(drop=True)
    radiant_ids_raw = sub[rad_cols].astype(np.int64).to_numpy()
    dire_ids_raw = sub[dir_cols].astype(np.int64).to_numpy()

    create_map = id_to_idx_map is None
    if create_map:
        all_ids = np.concatenate([radiant_ids_raw.ravel(), dire_ids_raw.ravel()])
        uniq_ids = np.unique(all_ids)
        id_to_idx_map = {int(h): i for i, h in enumerate(uniq_ids)}

    known = set(id_to_idx_map.keys())
    all_heroes = np.concatenate([radiant_ids_raw, dire_ids_raw], axis=1)
    valid = np.array([all(int(h) in known for h in row) for row in all_heroes])
    dropped = (~valid).sum()
    if dropped > 0:
        print(f"Dropping {dropped} matches with unknown heroes")
        sub = sub[valid].reset_index(drop=True)
        radiant_ids_raw = radiant_ids_raw[valid]
        dire_ids_raw = dire_ids_raw[valid]

    num_heroes = len(id_to_idx_map)
    mapper = np.vectorize(id_to_idx_map.get, otypes=[np.int64])
    radiant_ids = mapper(radiant_ids_raw)
    dire_ids = mapper(dire_ids_raw)
    y = sub["radiant_win"].astype(int).to_numpy()
    print(f"Processed {len(sub)} valid matches.")
    return radiant_ids, dire_ids, y, num_heroes, id_to_idx_map


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


class HybridDraftDataset(Dataset):
    def __init__(self, radiant_ids, dire_ids, y, hero_feature_matrix):
        self.radiant_ids = radiant_ids
        self.dire_ids = dire_ids
        self.y = y
        self.hero_features = hero_feature_matrix

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        hero_indices_np = np.concatenate([self.radiant_ids[idx], self.dire_ids[idx]])
        draft_features = self.hero_features[hero_indices_np]
        y_tensor = torch.tensor([int(self.y[idx])], dtype=torch.long)
        g = Data(
            x=draft_features,
            hero_indices=torch.from_numpy(hero_indices_np).long(),
            edge_index=EDGE_INDEX,
            edge_type=EDGE_TYPE,
            y=y_tensor,
        )
        g.num_nodes = 10
        return g


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
        edge_index = data.edge_index
        edge_type = data.edge_type
        batch = data.batch

        emb = self.hero_embedding(hero_idx)
        x = torch.cat([x, emb], dim=-1)

        x = self.bn1(self.conv1(x, edge_index, edge_type)).relu()
        x = self.dropout(x)
        x = self.bn2(self.conv2(x, edge_index, edge_type)).relu()
        x = self.dropout(x)

        num_graphs = batch.max().item() + 1
        x_per_graph = x.view(num_graphs, 10, -1)

        radiant_pool = x_per_graph[:, :5, :].mean(dim=1)
        dire_pool = x_per_graph[:, 5:, :].mean(dim=1)
        diff = radiant_pool - dire_pool
        interaction = radiant_pool * dire_pool

        combined = torch.cat([radiant_pool, dire_pool, diff, interaction], dim=1)
        return self.output_layer(combined).squeeze(1)


def main():
    device = get_default_device()
    print(f"Device: {device}")

    # Load data
    print("Loading public matches...")
    pub_df = load_pro_matches_parquet("../data/public_matches_dataset.parquet")

    print("Loading hero data...")
    with Path("../data/heroes_data.jsonl").open("r") as f:
        heroes = json.load(f)
    hero_objects = [HeroData.model_validate(h) for h in heroes]

    # Split
    train_df, test_df = train_test_split(pub_df, test_size=0.2, shuffle=False, random_state=42)
    radiant_ids, dire_ids, y, num_heroes, id_to_idx = prepare_draft_arrays(train_df)
    hero_features = create_hero_feature_matrix(hero_objects, id_to_idx)
    feature_dim = hero_features.shape[1]

    del train_df
    gc.collect()

    # Hyperparameters
    HP = {
        "hidden_dim": 128, "embedding_dim": 64, "lr": 1e-3,
        "dropout_rate": 0.2, "weight_decay": 0,
        "epochs": 80, "batch_size": 2048, "patience": 15,
    }

    # Model
    model = HybridGCN(
        feature_dim=feature_dim, num_heroes=num_heroes,
        embedding_dim=HP["embedding_dim"], num_relations=3,
        hidden_dim=HP["hidden_dim"], dropout_rate=HP["dropout_rate"],
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=HP["lr"], weight_decay=HP["weight_decay"])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)
    criterion = nn.BCEWithLogitsLoss()

    # Dataset
    full_ds = HybridDraftDataset(radiant_ids, dire_ids, y, hero_features)
    n_val = int(len(full_ds) * 0.2)
    train_ds, val_ds = random_split(full_ds, [len(full_ds) - n_val, n_val])
    train_loader = DataLoader(train_ds, batch_size=HP["batch_size"], shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=HP["batch_size"], num_workers=0)

    print(f"\n--- Training HybridGCN ({HP['epochs']} epochs, patience={HP['patience']}) ---")
    print(f"Train: {len(train_ds)}, Val: {len(val_ds)}")

    best_val_acc = 0.0
    epochs_no_improve = 0

    for epoch in range(HP["epochs"]):
        # Train
        model.train()
        total_loss = 0
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            logits = model(batch)
            loss = criterion(logits, batch.y.float())
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item() * batch.num_graphs
        train_loss = total_loss / len(train_loader.dataset)

        # Eval
        model.eval()
        correct = 0
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(device)
                logits = model(batch)
                preds = (logits > 0).long()
                correct += (preds.cpu() == batch.y.cpu()).sum().item()
        val_acc = correct / len(val_loader.dataset)

        lr_now = optimizer.param_groups[0]['lr']
        print(f"Epoch {epoch+1:02d}/{HP['epochs']} | Loss: {train_loss:.4f} | Val Acc: {val_acc:.4f} | LR: {lr_now:.1e}")

        scheduler.step(val_acc)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            epochs_no_improve = 0
            torch.save(model.state_dict(), "best_hybrid_gcn.pth")
            print(f"  -> Best model saved: {best_val_acc:.4f}")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= HP["patience"]:
                print(f"  -> Early stopping at epoch {epoch+1}")
                break

    print(f"\nBest validation accuracy: {best_val_acc:.4f}")

    # Test
    print("\n--- Evaluating on Holdout Test Set ---")
    model.load_state_dict(torch.load("best_hybrid_gcn.pth", weights_only=True))
    r_test, d_test, y_test, _, _ = prepare_draft_arrays(test_df, id_to_idx_map=id_to_idx)
    test_ds = HybridDraftDataset(r_test, d_test, y_test, hero_features)
    test_loader = DataLoader(test_ds, batch_size=HP["batch_size"], num_workers=0)

    model.eval()
    correct = 0
    with torch.no_grad():
        for batch in test_loader:
            batch = batch.to(device)
            logits = model(batch)
            preds = (logits > 0).long()
            correct += (preds.cpu() == batch.y.cpu()).sum().item()
    test_acc = correct / len(test_loader.dataset)
    print(f"Test Accuracy: {test_acc:.4f}")


if __name__ == "__main__":
    main()
