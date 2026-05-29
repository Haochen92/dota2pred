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

- **Result**: ~52.97%, stuck at loss 0.6913 (= ln(2), coin flip)
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

Output head changed from `Linear(hidden_dim, 1)` to `Linear(4*hidden_dim, hidden_dim) -> ReLU -> Dropout -> Linear(hidden_dim, 1)`.

**The model was never given a fair test. It must be rerun.**

### 6. Hero Attribute Transformer

- **Approach**: Static hero attributes (base stats, roles, attack type) as team-level count features
- **Implementation**: `lib/hero_features/hero_attributes_transformer.py`
- **Status**: Implemented but not evaluated standalone. Used as part of the HybridGCN feature matrix (29 features).

---

## What To Try Next (Priority Order)

### 1. Rerun Fixed GNN (HIGH — architectural bug was blocking learning)

The GNN never had a fair test. With team-aware pooling, it should at minimum break out of the 52.97% plateau. Run both:

- **RelationalGCN** (embedding-only) on pro matches — already fixed in `graph_network.ipynb`
- **HybridGCN** (static attributes + learnable embeddings) on public matches — already fixed

Use `shuffle=False` in `train_test_split` for temporal correctness (the public matches cell currently has `shuffle=True`).

Suggested hyperparameters to try if the default still struggles:

| Param | Current | Try |
|---|---|---|
| lr | 1e-4 / 3e-4 | 1e-3 |
| dropout | 0.5 / 0.4 | 0.2 |
| hidden_dim | 256 | 128 |
| emb_dim | 128 | 64 |
| weight_decay | 1e-5 | 0 |

The old config was too regularized (high dropout + weight decay + low lr) for a model that couldn't learn. Start aggressive, then regularize once it's training.

### 2. Word2Vec Centroid + Existing Features (MEDIUM — cheap experiment, ~30 min)

Test whether draft composition signal is complementary to existing performance-based features:

1. Train Word2Vec on training data (already done, `vector_size=32`)
2. Compute `radiant_centroid - dire_centroid` = 32 dims (instead of concatenating all 320)
3. Append to existing 4 features -> 36 total
4. Train LightGBM on combined feature set
5. Compare to 58.22% baseline

If the combined set beats 58.5%+, the draft composition signal is additive. If not, the existing decay features already capture what W2V learns.

### 3. GNN as Feature Extractor (LOW — only if GNN trains well)

If the fixed GNN reaches >55% standalone:

1. Train the GNN, freeze it
2. Extract the `combined` vector (4 * hidden_dim) before the output head
3. Use as features alongside the existing 4 decay features in a LightGBM
4. This lets GNN capture nonlinear draft interactions while decay features capture temporal performance

### 4. NOT worth pursuing

- **Sentence Transformer on hero IDs**: fundamentally wrong tool (pre-trained on English text, used frozen)
- **Multi-hot encoding**: team-agnostic by design, correctly ruled out
- **Further hyperparameter tuning on existing features**: landscape is flat, proven with McNemar's test
- **More complex models on same 4 features**: accuracy ceiling is ~58% with these features; model complexity is not the bottleneck

---

## File Locations

| What | Path |
|---|---|
| Feature tuning (Optuna) | `model_factory/notebook/feature_tuning.ipynb` |
| Model tuning (Optuna) | `model_factory/notebook/model_tuning.ipynb` |
| Feature engineering experiments | `model_factory/notebook/feature_engineering.ipynb` |
| DL experiments (multi-hot, W2V) | `model_factory/notebook/nonlinear_models_experiment.ipynb` |
| GNN experiments (FIXED) | `model_factory/notebook/graph_network.ipynb` |
| Tuning library (Optuna wrappers) | `model_factory/notebook/lib/hyperparams/` |
| Hero feature creators | `model_factory/notebook/lib/hero_features/` |
| Production feature hyperparams | `dota_oracle_schedules/src/dota_oracle_schedules/ml_pipelines/backfill_feature_engineering.py` |
| Production inference service | `services/inference_service/src/inference_service/service.py` |
| Model save/deploy | `model_factory/src/model_factory/save_model.py` |
| Pro match training notebook | `model_factory/notebook/pro_matches_model.ipynb` |
| Public match training notebook | `model_factory/notebook/pub_matches_model.ipynb` |
