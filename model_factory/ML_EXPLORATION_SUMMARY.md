# ML Exploration Summary

## Current Production Model

- **Algorithm**: Logistic Regression (chosen for simplicity over ~1% accuracy gain from LightGBM)
- **Features**: 4 aggregated difference features with VIF < 1.6
  1. `radiant_dire_team_wr_diff` — team win rate difference
  2. `radiant_dire_matchup` — head-to-head matchup history
  3. `radiant_dire_hero_wr_diff` — average hero winrate difference
  4. `radiant_dire_player_hero_wr_diff` — player-hero skill difference
- **Test accuracy**: 57.15% (LogReg), 58.22% (LightGBM on granular features)
- **Baseline**: 51.8% (always predict Radiant)
- **Production accuracy**: ~58%, matching test — no overfitting

### Feature Engineering

Three tiers of time-decayed Bayesian features:

| Feature Set | Hyperparameters | Key Design |
|---|---|---|
| Team | prior_mean=0.52, prior_count=13, half_life=45d | Exponential decay + Bayesian prior |
| Hero | prior_mean=0.50, prior_count=50, half_life=45d | Global hero win rates with decay |
| Player-Hero | player_prior_count=8, player_half_life=60d | Two-level Bayesian smoothing (hero prior for sparse player-hero pairs) |

### Hyperparameter Tuning Conclusion

Optuna studies (165 trials simultaneous, 60 trials targeted) showed the landscape is flat. McNemar's test confirmed tuned vs. default is not statistically significant (p=0.66). Principled defaults based on domain knowledge match algorithmic optimization.

---

## Deep Learning Experiments Conducted

### 1. Multi-Hot Encoding (MultiLabelBinarizer)

- **Result**: 51.9% (worse than baseline)
- **Conclusion**: Correctly identified as team-agnostic. Treats the 10-hero draft as a single bag of heroes, erasing Radiant vs. Dire distinction. The prediction target is `radiant_win`, so symmetric features make learning impossible.
- **Status**: Dead end, well understood.

### 2. Contrastive Word2Vec Embeddings

- **Result**: 53.3% (LogReg best, all models tried)
- **Approach**: Treat each team draft as a "sentence", prepend WIN/LOSS token, train Word2Vec on these contrastive sentences. Generate team centroids from learned hero vectors.
- **Implementation**: `lib/hero_features/word_to_vec.py`, vector_size=32, Skip-gram
- **Issue**: The `transform()` concatenates all 10 hero vectors = 320 features for ~40K samples (curse of dimensionality). Only tested with default model hyperparameters.
- **Status**: Has potential. See "Next Steps" below.

### 3. Sentence Transformer (all-MiniLM-L6-v2)

- **Result**: Not run to completion
- **Approach**: Encode hero drafts as text strings (`"hero_55 hero_18 ..."`) using a pre-trained NLP sentence transformer.
- **Implementation**: `lib/hero_features/sentence_transformer.py`
- **Issue**: Fundamentally misapplied. The model was pre-trained on English text and is used frozen (no fine-tuning). `"hero_55"` has no semantic meaning to it — the embeddings are essentially random with respect to actual hero properties.
- **Status**: Dead end. Would need a domain-specific embedding model, not an English text model.

### 4. PyTorch Supervised Embedding (MLP)

- **Approach**: Learnable embedding per hero -> mean pool per team -> concat(radiant_mean, dire_mean, diff, multiplication) -> MLP classifier head
- **Implementation**: `lib/hero_features/dl_hero_embedding.py`
- **Architecture**: Embedding(150, 32) -> team mean pool -> 4*32=128 -> Linear(128,128) -> BatchNorm -> Dropout(0.3) -> Linear(128,64) -> BatchNorm -> Dropout(0.3) -> Linear(64,1)
- **Note**: This model correctly uses team-aware pooling (separate radiant/dire). Early stopping with patience=10.
- **Status**: Architecture is sound. Results not captured in notebook output.

### 5. Relational GCN (Graph Neural Network)

- **Approach**: Model draft as a graph with 10 nodes. Three edge types: synergy (same team), counter (opposite team), self-loop. Two layers of RGCNConv.
- **Implementation**: `graph_network.ipynb`, cells `aacacbf4` (RelationalGCN) and `5bf9a594` (HybridGCN)

#### BUG FOUND AND FIXED (2026-05-29)

Both `RelationalGCN` and `HybridGCN` had a critical bug: `global_add_pool(x, batch)` pooled ALL 10 nodes into one vector, making the readout **team-agnostic** — the exact same flaw identified in the multi-hot encoding experiment.

**Fix applied**: Team-aware pooling that separates Radiant (nodes 0-4) and Dire (nodes 5-9):

```python
# BEFORE (broken)
x = global_add_pool(x, batch)
logits = self.output_layer(x)  # Linear(hidden_dim, 1)

# AFTER (fixed)
x_per_graph = x.view(num_graphs, 10, -1)
radiant_pool = x_per_graph[:, :5, :].mean(dim=1)
dire_pool    = x_per_graph[:, 5:, :].mean(dim=1)
diff         = radiant_pool - dire_pool
interaction  = radiant_pool * dire_pool
combined     = cat([radiant_pool, dire_pool, diff, interaction])  # 4 * hidden_dim
```

Output head changed from `Linear(hidden_dim, 1)` to `Linear(4*hidden_dim, hidden_dim) -> BatchNorm -> ReLU -> Dropout -> Linear(hidden_dim, 1)`.

#### RERUN RESULTS (2026-05-29)

Additional fixes applied for rerun: BatchNorm after each RGCNConv layer, gradient clipping (max_norm=1.0), ReduceLROnPlateau scheduler, early stopping with patience=15. Hyperparameters made more aggressive (lr=1e-3, dropout=0.2, hidden_dim=128, emb_dim=64, weight_decay=0).

**Bug in HybridGCN**: `create_hero_feature_matrix()` crashed with NaN because Undying (id=85) has `base_health_regen = None`. Fixed with `getattr(hero, col) or 0`.

| Experiment | Model | Data | Val Acc | Test Acc | Notes |
|---|---|---|---|---|---|
| 1 | RelationalGCN (embeddings only) | Pro matches (32K) | 53.73% | **52.79%** | Data-starved; early stopped epoch 21 |
| 2 | RelationalGCN (embeddings only) | Public matches (555K) | 56.47% | **55.52%** | More data = +2.7% test over pro |
| 3 | HybridGCN (embeddings + 29-dim hero attrs) | Public matches (555K) | 56.66% | **55.82%** | Static features add +0.3% over embeddings alone |

**Key findings**:
- Team-aware pooling fix worked — all models broke past the old 52.97% plateau
- Data volume matters significantly (32K → 555K = +2.7% test accuracy)
- Static hero attributes (base stats, roles, attack type) add marginal value (+0.3%); learnable embeddings capture most of the signal
- Draft-only GNN reaches ~55-56% on public matches, ~2-3% below production LightGBM (58.22%) which uses performance history features
- The GNN learns orthogonal signal (hero synergies/counters from draft structure) vs production model (team/player temporal performance) — promising for stacking
- Train/test splits are temporal (shuffle=False); train/val splits within training are random
- Pro matches need more data (180K+ available in remote DB) or transfer learning (pre-train on public, fine-tune on pro)

### 6. Hero Attribute Transformer

- **Approach**: Static hero attributes (base stats, roles, attack type) as team-level count features
- **Implementation**: `lib/hero_features/hero_attributes_transformer.py`
- **Status**: Evaluated as part of HybridGCN (experiment 3 above). Adds +0.3% over embeddings alone.

### 7. GNN Stacking Experiment (2026-05-29)

Tested whether GNN draft embeddings add value on top of Bayesian hero win rate features on public matches (555K). Extracted 512-dim `combined` vector from frozen HybridGCN, stacked with hero WR features in LightGBM.

| Model | Features | Test Acc | vs Baseline |
| --- | --- | --- | --- |
| **Granular WRs + GNN raw-512** | 523 | **56.09%** | **+1.33%** |
| GNN only (raw-512) | 512 | 55.89% | +1.13% |
| Hero WR + GNN PCA-32 | 33 | 55.82% | +1.06% |
| Granular WRs + GNN PCA-32 | 43 | 55.74% | +0.98% |
| GNN only (PCA-32) | 32 | 55.70% | +0.95% |
| Granular hero WRs (baseline) | 11 | 54.76% | — |
| Hero WR diff only | 1 | 54.75% | -0.01% |

**Key findings**:

- GNN embeddings add **+1.33%** over hero WR features — draft synergy/counter signal is real and additive
- GNN dominates feature importance: 14 of top 15 LightGBM features are GNN PCA components
- Raw 512-dim slightly outperforms PCA-32 — LightGBM handles the dimensionality
- Granular per-hero WRs (11 features) don't help over single diff — individual hero WRs lack pairwise interaction signal
- **Caveat**: This is hero-only features on public matches. The production pro model (58.22%) also uses team WR, matchup, and player-hero features. Whether GNN adds value on top of the full 4-feature pro set remains untested (requires team/player IDs from remote DB)

**Implementation**: `model_factory/notebook/run_stacking_experiment.py`

---

## What To Try Next (Priority Order)

### 1. Stack GNN with Full Pro Features (HIGH — the real production test)

The stacking experiment proved GNN adds +1.33% over hero-only features on public matches. The critical unanswered question: does it also add value on top of the full 4-feature production set (team WR, matchup, hero WR, player-hero WR) on pro matches?

This requires pro matches with team/player IDs from the remote DB. Approach:

1. Export pro matches (ideally all 180K+) from remote DB
2. Compute all 4 Bayesian features
3. Extract GNN embeddings using the public-trained HybridGCN (transfer)
4. Stack in LightGBM and compare to 58.22% baseline
5. If it beats 58.5%+, integrate GNN into the production pipeline

### 2. Pre-train on Public, Fine-tune on Pro (HIGH — addresses data scarcity)

The pro match GNN (52.79%) was data-starved with only 32K matches. Transfer learning approach:

1. Pre-train HybridGCN on 555K public matches (done)
2. Freeze conv layers, replace output head
3. Fine-tune output head + embeddings on pro matches (32K, or ideally 180K from remote DB)
4. The model learns general hero synergies from public games, then adapts to pro-specific patterns

### 3. Export Full Pro Match Dataset (MEDIUM — enables #1 and #2)

Currently only 32K pro matches (patches 7.37-7.39) are exported locally. The remote DB has 180K+ matches. More data would significantly help both the stacking test and pro-specific GNN training. Could add patch features or time-decay weighting to handle meta shifts across patches.

### 4. NOT worth pursuing

- **Sentence Transformer on hero IDs**: fundamentally wrong tool (pre-trained on English text, used frozen)
- **Multi-hot encoding**: team-agnostic by design, correctly ruled out
- **Further hyperparameter tuning on existing features**: landscape is flat, proven with McNemar's test
- **More complex models on same 4 features**: accuracy ceiling is ~58% with these features; model complexity is not the bottleneck
- **Word2Vec centroid features**: GNN stacking already proves draft composition is additive; W2V would be a weaker version of the same signal

---

## File Locations

| What | Path |
|---|---|
| Feature tuning (Optuna) | `model_factory/notebook/feature_tuning.ipynb` |
| Model tuning (Optuna) | `model_factory/notebook/model_tuning.ipynb` |
| Feature engineering experiments | `model_factory/notebook/feature_engineering.ipynb` |
| DL experiments (multi-hot, W2V) | `model_factory/notebook/nonlinear_models_experiment.ipynb` |
| GNN experiments (FIXED) | `model_factory/notebook/graph_network.ipynb` |
| GNN experiment 3 standalone script | `model_factory/notebook/run_hybrid_gcn.py` |
| Tuning library (Optuna wrappers) | `model_factory/notebook/lib/hyperparams/` |
| Hero feature creators | `model_factory/notebook/lib/hero_features/` |
| Production feature hyperparams | `dota_oracle_schedules/src/dota_oracle_schedules/ml_pipelines/backfill_feature_engineering.py` |
| Production inference service | `services/inference_service/src/inference_service/service.py` |
| Model save/deploy | `model_factory/src/model_factory/save_model.py` |
| Pro match training notebook | `model_factory/notebook/pro_matches_model.ipynb` |
| Public match training notebook | `model_factory/notebook/pub_matches_model.ipynb` |
