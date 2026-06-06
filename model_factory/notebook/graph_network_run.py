# === Cell 0 (id: 4b052e7e) ===
import torch, torch_geometric
import pandas as pd
import numpy as np

# === Cell 1 (id: cb6d365a) ===
print(torch.__version__)
print(torch.backends.mps.is_available())
print(torch_geometric.__version__)

# === Cell 2 (id: 54073d5a) ===
from lib.data_management import load_match_tables_jsonl

# === Cell 3 (id: c180562f) ===
data_path = "../data/pro_match_tables.jsonl"

matches = load_match_tables_jsonl(data_path)

matches[:10]

# === Cell 4 (id: d87d7b5b) ===
match = matches[0]
match.outcome

# === Cell 5 (id: cbab54b0) ===
outcome_df = pd.DataFrame([m.outcome.model_dump() for m in matches if m.outcome is not None])
outcome_df

# === Cell 6 (id: b6afbcb5) ===
df = pd.DataFrame([match.model_dump() for match in matches])
df

# === Cell 7 (id: fd976c5c) ===
combined_df = df.merge(outcome_df, on="match_id", how='inner')

# === Cell 8 (id: d069029c) ===
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch import nn
from torch_geometric.nn.aggr import AttentionalAggregation 
from torch.utils.data import random_split

from torch_geometric.nn import RGCNConv

# === Cell 9 (id: aacacbf4) ===
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import random_split
from sklearn.model_selection import train_test_split

from torch_geometric.nn import GCNConv, global_mean_pool, global_add_pool, global_max_pool
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

def get_default_device():
    if torch.cuda.is_available():
        return torch.device('cuda')
    elif torch.backends.mps.is_available():
        return torch.device('mps')
    else:
        return torch.device('cpu')


def prepare_draft_arrays(df: pd.DataFrame, id_to_idx_map: dict = None):
    rad_cols = [f"slot_{i}_hero_id" for i in range(5)]
    dir_cols = [f"slot_{i}_hero_id" for i in range(128, 133)]
    
    sub = df.dropna(subset=rad_cols + dir_cols).copy()
    sub.reset_index(drop=True, inplace=True)
    
    radiant_ids_raw = sub[rad_cols].astype(np.int64).to_numpy()
    dire_ids_raw = sub[dir_cols].astype(np.int64).to_numpy()
    
    create_map = id_to_idx_map is None
    if create_map:
        all_ids = np.concatenate([radiant_ids_raw.reshape(-1), dire_ids_raw.reshape(-1)])
        uniq = np.unique(all_ids)
        id_to_idx_map = {int(h): i for i, h in enumerate(uniq)}

    num_heroes = len(id_to_idx_map)
    
    all_known_heroes = set(id_to_idx_map.keys())
    valid_rows_mask = np.array([
        all(hero in all_known_heroes for hero in row) 
        for row in np.concatenate([radiant_ids_raw, dire_ids_raw], axis=1)
    ])
    
    if np.sum(~valid_rows_mask) > 0:
        print(f"Dropping {np.sum(~valid_rows_mask)} matches with unknown heroes")
        sub = sub[valid_rows_mask].reset_index(drop=True)
        radiant_ids_raw = radiant_ids_raw[valid_rows_mask]
        dire_ids_raw = dire_ids_raw[valid_rows_mask]
    
    print(f"Processed {len(sub)} valid matches.")
    
    mapper = np.vectorize(id_to_idx_map.get, otypes=[np.int64])
    radiant_ids = mapper(radiant_ids_raw)
    dire_ids = mapper(dire_ids_raw)
    
    if "radiant_win" in sub.columns:
        y = sub["radiant_win"].astype(int).to_numpy()
    else:
        raise ValueError("No 'radiant_win' label column found.")
        
    if create_map:
        return radiant_ids, dire_ids, y, num_heroes, id_to_idx_map
    else:
        return radiant_ids, dire_ids, y, num_heroes


def build_relational_edges_for_10_nodes():
    radiant_nodes = list(range(5))
    dire_nodes = list(range(5, 10))
    
    edges = []
    edge_types = []
    
    for team in (radiant_nodes, dire_nodes):
        for i in team:
            for j in team:
                if i != j:
                    edges.append((i, j))
                    edge_types.append(0)
                    
    for i in radiant_nodes:
        for j in dire_nodes:
            edges.append((i, j))
            edge_types.append(1)
            edges.append((j, i))
            edge_types.append(1)
            
    for i in range(10):
        edges.append((i, i))
        edge_types.append(2)
        
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    edge_type = torch.tensor(edge_types, dtype=torch.long)
    
    return edge_index, edge_type

RELATIONAL_EDGE_INDEX, RELATIONAL_EDGE_TYPE = build_relational_edges_for_10_nodes()


def make_relational_graphs_from_arrays(r_ids_np, d_ids_np, y_np):
    data_list = []
    for r5, d5, y in zip(r_ids_np, d_ids_np, y_np):
        hero_indices = torch.tensor(np.concatenate([r5, d5]), dtype=torch.long)
        y_tensor = torch.tensor([int(y)], dtype=torch.long)
        g = Data(
            x=hero_indices,
            edge_index=RELATIONAL_EDGE_INDEX,
            edge_type=RELATIONAL_EDGE_TYPE,
            y=y_tensor
        )
        g.num_nodes = 10
        data_list.append(g)
    return data_list


class RelationalGCN(nn.Module):
    def __init__(self, num_heroes, num_relations, emb_dim, hidden_dim, dropout_rate=0.2):
        super().__init__()
        self.embedding = nn.Embedding(num_heroes, emb_dim)
        
        self.conv1 = RGCNConv(emb_dim, hidden_dim, num_relations)
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

    def forward(self, data: Data) -> torch.Tensor:
        x, edge_index, edge_type, batch = data.x, data.edge_index, data.edge_type, data.batch
        
        x = self.embedding(x)
        
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
        logits = self.output_layer(combined)
        return logits.squeeze(1)

# === Cell 10 (id: 63ca766e) ===
from torch.utils.data import Dataset

class DotaDraftDataset(Dataset):
    def __init__(self, radiant_ids, dire_ids, y):
        self.radiant_ids = radiant_ids
        self.dire_ids = dire_ids
        self.y = y

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        # Fetch data for a single match
        r5_id = self.radiant_ids[idx]
        d5_id = self.dire_ids[idx]
        y_val = self.y[idx]

        # Create the graph object just-in-time
        hero_indices = torch.tensor(np.concatenate([r5_id, d5_id]), dtype=torch.long)
        y_tensor = torch.tensor([int(y_val)], dtype=torch.long)
        
        g = Data(
            x=hero_indices,
            edge_index=RELATIONAL_EDGE_INDEX, # Assumes this is a global constant
            edge_type=RELATIONAL_EDGE_TYPE,   # Assumes this is a global constant
            y=y_tensor
        )
        g.num_nodes = 10
        return g

# === Cell 11 (id: 5ff09a1e) ===
from torch.utils.data import Dataset

class DotaDraftDataset(Dataset):
    def __init__(self, radiant_ids, dire_ids, y):
        self.radiant_ids = radiant_ids
        self.dire_ids = dire_ids
        self.y = y

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        r5_id = self.radiant_ids[idx]
        d5_id = self.dire_ids[idx]
        y_val = self.y[idx]

        hero_indices = torch.tensor(np.concatenate([r5_id, d5_id]), dtype=torch.long)
        y_tensor = torch.tensor([int(y_val)], dtype=torch.long)
        
        g = Data(
            x=hero_indices,
            edge_index=RELATIONAL_EDGE_INDEX,
            edge_type=RELATIONAL_EDGE_TYPE,
            y=y_tensor
        )
        g.num_nodes = 10
        return g


class GNNTrainer:
    def __init__(self, num_heroes, emb_dim, hidden_dim, lr, dropout_rate, weight_decay=0.0):
        self.device = get_default_device()
        print(f"GNNTrainer using device: {self.device}")

        self.model = RelationalGCN(
            num_heroes=num_heroes, num_relations=3, emb_dim=emb_dim,
            hidden_dim=hidden_dim, dropout_rate=dropout_rate
        ).to(self.device)
        
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='max', factor=0.5, patience=5
        )
        self.criterion = nn.BCEWithLogitsLoss()

    def _train_one_epoch(self, loader):
        self.model.train()
        total_loss = 0
        for batch in loader:
            batch = batch.to(self.device)
            self.optimizer.zero_grad()
            logits = self.model(batch)
            loss = self.criterion(logits, batch.y.float())
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            total_loss += loss.item() * batch.num_graphs
        return total_loss / len(loader.dataset)

    @torch.no_grad()
    def _evaluate(self, loader):
        self.model.eval()
        correct = 0
        for batch in loader:
            batch = batch.to(self.device)
            logits = self.model(batch)
            preds = (logits > 0).long()
            correct += (preds.cpu() == batch.y.cpu()).sum().item()
        return correct / len(loader.dataset)

    def fit(self, radiant_ids, dire_ids, y, epochs=80, batch_size=2048, val_ratio=0.2, patience=15):
        print(f"\n--- Training RelationalGCN ({epochs} epochs, patience={patience}) ---")
        full_dataset = DotaDraftDataset(radiant_ids, dire_ids, y)
        
        n_val = int(len(full_dataset) * val_ratio)
        n_train = len(full_dataset) - n_val
        train_ds, val_ds = random_split(full_dataset, [n_train, n_val])
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=batch_size, num_workers=0)
        
        print(f"Train: {len(train_ds)}, Val: {len(val_ds)}")

        best_val_acc = 0.0
        epochs_no_improve = 0

        for epoch in range(epochs):
            train_loss = self._train_one_epoch(train_loader)
            val_acc = self._evaluate(val_loader)
            lr_now = self.optimizer.param_groups[0]['lr']
            print(f"Epoch {epoch+1:02d}/{epochs} | Loss: {train_loss:.4f} | Val Acc: {val_acc:.4f} | LR: {lr_now:.1e}")

            self.scheduler.step(val_acc)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                epochs_no_improve = 0
                torch.save(self.model.state_dict(), "best_rgcn_model.pth")
                print(f"  -> Best model saved: {best_val_acc:.4f}")
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    print(f"  -> Early stopping at epoch {epoch+1}")
                    break
        
        print(f"\nBest validation accuracy: {best_val_acc:.4f}")
        self.model.load_state_dict(torch.load("best_rgcn_model.pth", weights_only=True))

    def evaluate_on_test_set(self, test_df, id_to_idx, batch_size):
        print("\n--- Evaluating on Holdout Test Set ---")
        r_ids, d_ids, y_test, _ = prepare_draft_arrays(test_df, id_to_idx_map=id_to_idx)
        test_dataset = make_relational_graphs_from_arrays(r_ids, d_ids, y_test)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, num_workers=0)
        test_acc = self._evaluate(test_loader)
        print(f"Test Accuracy: {test_acc:.4f}")
        return test_acc

# === Cell 12 (id: fa6e0ed8) ===
train_df, test_df = train_test_split(combined_df, test_size=0.2, shuffle=False, random_state=42)

radiant_ids, dire_ids, y, num_heroes, id_to_idx = prepare_draft_arrays(train_df)

HP = {
    "emb_dim": 64, "hidden_dim": 128, "lr": 1e-3, "dropout_rate": 0.2,
    "epochs": 80, "batch_size": 2048, "weight_decay": 0, "patience": 15
}

simple_trainer = GNNTrainer(
    num_heroes=num_heroes, emb_dim=HP["emb_dim"], hidden_dim=HP["hidden_dim"],
    lr=HP["lr"], dropout_rate=HP["dropout_rate"], weight_decay=HP["weight_decay"]
)
simple_trainer.fit(
    radiant_ids, dire_ids, y,
    epochs=HP["epochs"], batch_size=HP["batch_size"], patience=HP["patience"]
)

simple_trainer.evaluate_on_test_set(test_df, id_to_idx, batch_size=HP["batch_size"])

# === Cell 13 (id: 022d1396) ===
from lib.data_management import load_pro_matches_parquet

# === Cell 14 (id: cb222f7a) ===
pub_patch_fp = "../data/public_matches_dataset.parquet"

pub_matches_df = load_pro_matches_parquet(pub_patch_fp)

# === Cell 15 (id: 5db6e5e5) ===
pub_matches_df

# === Cell 16 (id: 337d3a08) ===
train_df, test_df = train_test_split(pub_matches_df, test_size=0.2, shuffle=False, random_state=42)

radiant_ids, dire_ids, y, num_heroes, id_to_idx = prepare_draft_arrays(train_df)

HP = {
    "emb_dim": 64, "hidden_dim": 128, "lr": 1e-3, "dropout_rate": 0.2,
    "epochs": 80, "batch_size": 2048, "weight_decay": 0, "patience": 15
}

simple_trainer = GNNTrainer(
    num_heroes=num_heroes, emb_dim=HP["emb_dim"], hidden_dim=HP["hidden_dim"],
    lr=HP["lr"], dropout_rate=HP["dropout_rate"], weight_decay=HP["weight_decay"]
)
simple_trainer.fit(
    radiant_ids, dire_ids, y,
    epochs=HP["epochs"], batch_size=HP["batch_size"], patience=HP["patience"]
)

simple_trainer.evaluate_on_test_set(test_df, id_to_idx, batch_size=HP["batch_size"])

# === Cell 17 (id: 1c0ac1b9) ===
from pathlib import Path
import json
from dota_oracle_common.models.heroes import HeroData

heros_path = Path("../data/heroes_data.jsonl")
with heros_path.open("r", encoding="utf-8") as f:
    heroes = json.load(f)

hero_objects = [HeroData.model_validate(hero) for hero in heroes]
hero_objects[:5]

# === Cell 18 (id: 5bf9a594) ===
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import gc
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MultiLabelBinarizer
from torch.utils.data import Dataset, random_split

from torch_geometric.nn import RGCNConv
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

# ==============================================================================
# PART 1: FEATURE ENGINEERING
# ==============================================================================

def create_hero_feature_matrix(hero_objects, id_to_idx_map):
    hero_data_dict = {h.id: h for h in hero_objects}
    num_heroes = len(id_to_idx_map)
    
    numerical_cols = [
        'agi_gain', 'base_agi', 'int_gain', 'base_int', 'str_gain', 'base_str',
        'attack_rate', 'attack_range', 'attack_point', 'projectile_speed',
        'base_armor', 'base_mana', 'base_mana_regen', 'base_health', 'base_health_regen'
    ]
    numerical_features_list = [
        [getattr(hero_data_dict[h_id], col) for col in numerical_cols]
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
    
    combined_features_temp = np.concatenate([
        numerical_features_scaled, attr_one_hot, attack_type_one_hot, roles_multi_hot
    ], axis=1)
    
    feature_dim = combined_features_temp.shape[1]
    print(f"Created hero feature matrix: [{num_heroes}, {feature_dim}]")
    
    final_feature_matrix = np.zeros((num_heroes, feature_dim))
    for hero_id, hero_idx in id_to_idx_map.items():
        original_pos = list(id_to_idx_map.keys()).index(hero_id)
        final_feature_matrix[hero_idx] = combined_features_temp[original_pos]
        
    return torch.tensor(final_feature_matrix, dtype=torch.float)

# ==============================================================================
# PART 2: DATA PIPELINE
# ==============================================================================

def prepare_draft_arrays(df: pd.DataFrame, id_to_idx_map=None):
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
    
    # Filter matches with unknown heroes
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

HYBRID_EDGE_INDEX, HYBRID_EDGE_TYPE = build_relational_edges()


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
            edge_index=HYBRID_EDGE_INDEX,
            edge_type=HYBRID_EDGE_TYPE,
            y=y_tensor,
        )
        g.num_nodes = 10
        return g

# ==============================================================================
# PART 3: MODEL ARCHITECTURE
# ==============================================================================

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

    def forward(self, data: Data) -> torch.Tensor:
        precomputed_features = data.x
        hero_indices = data.hero_indices
        edge_index = data.edge_index
        edge_type = data.edge_type
        batch = data.batch
        
        learnable_embeddings = self.hero_embedding(hero_indices)
        x = torch.cat([precomputed_features, learnable_embeddings], dim=-1)
        
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
        logits = self.output_layer(combined)
        return logits.squeeze(1)

# ==============================================================================
# PART 4: TRAINER
# ==============================================================================

class HybridGNNTrainer:
    def __init__(self, feature_dim, num_heroes, embedding_dim, hidden_dim, lr, dropout_rate, weight_decay):
        self.device = get_default_device()
        print(f"HybridGNNTrainer using device: {self.device}")

        self.model = HybridGCN(
            feature_dim=feature_dim,
            num_heroes=num_heroes,
            embedding_dim=embedding_dim,
            num_relations=3,
            hidden_dim=hidden_dim,
            dropout_rate=dropout_rate,
        ).to(self.device)
        
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='max', factor=0.5, patience=5
        )
        self.criterion = nn.BCEWithLogitsLoss()

    def _train_one_epoch(self, loader):
        self.model.train()
        total_loss = 0
        for batch in loader:
            batch = batch.to(self.device)
            self.optimizer.zero_grad()
            logits = self.model(batch)
            loss = self.criterion(logits, batch.y.float())
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            total_loss += loss.item() * batch.num_graphs
        return total_loss / len(loader.dataset)

    @torch.no_grad()
    def _evaluate(self, loader):
        self.model.eval()
        correct = 0
        for batch in loader:
            batch = batch.to(self.device)
            logits = self.model(batch)
            preds = (logits > 0).long()
            correct += (preds.cpu() == batch.y.cpu()).sum().item()
        return correct / len(loader.dataset)

    def fit(self, radiant_ids, dire_ids, y, hero_features, epochs=80, batch_size=2048, val_ratio=0.2, patience=15):
        print(f"\n--- Training HybridGCN ({epochs} epochs, patience={patience}) ---")
        full_dataset = HybridDraftDataset(radiant_ids, dire_ids, y, hero_features)
        
        n_val = int(len(full_dataset) * val_ratio)
        n_train = len(full_dataset) - n_val
        train_ds, val_ds = random_split(full_dataset, [n_train, n_val])
        
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=batch_size, num_workers=0)
        
        print(f"Train: {len(train_ds)}, Val: {len(val_ds)}")

        best_val_acc = 0.0
        epochs_no_improve = 0
        
        for epoch in range(epochs):
            train_loss = self._train_one_epoch(train_loader)
            val_acc = self._evaluate(val_loader)
            lr_now = self.optimizer.param_groups[0]['lr']
            print(f"Epoch {epoch+1:02d}/{epochs} | Loss: {train_loss:.4f} | Val Acc: {val_acc:.4f} | LR: {lr_now:.1e}")
            
            self.scheduler.step(val_acc)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                epochs_no_improve = 0
                torch.save(self.model.state_dict(), "best_hybrid_gcn.pth")
                print(f"  -> Best model saved: {best_val_acc:.4f}")
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    print(f"  -> Early stopping at epoch {epoch+1}")
                    break
        
        print(f"\nBest validation accuracy: {best_val_acc:.4f}")
        self.model.load_state_dict(torch.load("best_hybrid_gcn.pth", weights_only=True))

    def evaluate_on_test_set(self, test_df, id_to_idx, hero_features, batch_size):
        print("\n--- Evaluating on Holdout Test Set ---")
        r_ids, d_ids, y_test, _, _ = prepare_draft_arrays(test_df, id_to_idx_map=id_to_idx)

        test_dataset = HybridDraftDataset(r_ids, d_ids, y_test, hero_features)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, num_workers=0)

        test_acc = self._evaluate(test_loader)
        print(f"Test Accuracy: {test_acc:.4f}")
        return test_acc

# === Cell 19 (id: 3082ef8e) ===
train_df, test_df = train_test_split(pub_matches_df, test_size=0.2, shuffle=False, random_state=42)

radiant_ids, dire_ids, y, num_heroes, id_to_idx = prepare_draft_arrays(train_df)
hero_features = create_hero_feature_matrix(hero_objects, id_to_idx)
feature_dim = hero_features.shape[1]

del train_df
gc.collect()

HP = {
    "hidden_dim": 128,
    "embedding_dim": 64,
    "lr": 1e-3,
    "dropout_rate": 0.2,
    "weight_decay": 0,
    "epochs": 80,
    "batch_size": 2048,
    "patience": 15,
}

trainer = HybridGNNTrainer(
    feature_dim=feature_dim,
    num_heroes=num_heroes,
    embedding_dim=HP["embedding_dim"],
    hidden_dim=HP["hidden_dim"],
    lr=HP["lr"],
    dropout_rate=HP["dropout_rate"],
    weight_decay=HP["weight_decay"],
)

trainer.fit(
    radiant_ids, dire_ids, y,
    hero_features=hero_features,
    epochs=HP["epochs"],
    batch_size=HP["batch_size"],
    patience=HP["patience"],
)

trainer.evaluate_on_test_set(test_df, id_to_idx, hero_features, batch_size=HP["batch_size"])

