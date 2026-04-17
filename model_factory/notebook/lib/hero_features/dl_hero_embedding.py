import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from tqdm.auto import tqdm

# --- 1. The PyTorch Model Definition ---


class PyTorchHeroModel(nn.Module):
    """
    A PyTorch implementation of the supervised embedding model.
    The architecture is designed to be a direct equivalent of the Keras version.
    """

    def __init__(self, n_heroes=150, embedding_dim=32):
        super().__init__()
        self.n_heroes = n_heroes
        self.embedding_dim = embedding_dim

        # --- Layers ---
        # Embedding layer: a trainable lookup table
        self.hero_embedding = nn.Embedding(num_embeddings=self.n_heroes, embedding_dim=self.embedding_dim)

        # MLP Classifier Head: a sequence of layers
        # The input size is calculated as 4 * embedding_dim because we concatenate:
        # (radiant_mean, dire_mean, difference, multiplication)
        self.classifier = nn.Sequential(
            nn.Linear(4 * self.embedding_dim, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
            # Sigmoid is applied later in the loss function for numerical stability
        )

    def forward(self, x):
        """Defines the forward pass of the model."""
        # x has shape: (batch_size, 10)

        # 1. Get embeddings for all 10 heroes
        embedded_picks = self.hero_embedding(x)
        # -> shape: (batch_size, 10, embedding_dim)

        # 2. Separate into Radiant and Dire teams
        radiant_embedded = embedded_picks[:, :5, :]
        dire_embedded = embedded_picks[:, 5:, :]
        # -> shape: (batch_size, 5, embedding_dim)

        # 3. Pool to get team representations (equivalent to GlobalAveragePooling)
        radiant_team_vec = torch.mean(radiant_embedded, dim=1)
        dire_team_vec = torch.mean(dire_embedded, dim=1)
        # -> shape: (batch_size, embedding_dim)

        # 4. Create interaction features
        team_diff = radiant_team_vec - dire_team_vec
        team_mult = radiant_team_vec * dire_team_vec

        # 5. Combine features for the classifier
        combined = torch.cat([radiant_team_vec, dire_team_vec, team_diff, team_mult], dim=1)
        # -> shape: (batch_size, 4 * embedding_dim)

        # 6. Get the final prediction
        logits = self.classifier(combined)
        # -> shape: (batch_size, 1)

        return logits


# --- 2. Data Preparation and Training Loop ---


def train_pytorch_model(hero_df, n_heroes=150, embedding_dim=32, epochs=50, batch_size=256):
    """A standalone function to handle data loading and the training loop."""

    # --- Data Preparation ---
    X = torch.LongTensor(hero_df["hero_picks"].tolist())
    y = torch.FloatTensor(hero_df["radiant_win"].values.astype(float)).unsqueeze(1)  # Add dimension for loss

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    train_dataset = TensorDataset(X_train, y_train)
    val_dataset = TensorDataset(X_val, y_val)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)

    # --- Model, Optimizer, Loss ---
    model = PyTorchHeroModel(n_heroes=n_heroes, embedding_dim=embedding_dim)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    # BCEWithLogitsLoss is more numerically stable than using a Sigmoid layer + BCELoss
    criterion = nn.BCEWithLogitsLoss()

    # --- Training Loop ---
    best_val_accuracy = 0.0
    patience_counter = 0
    patience = 10  # For early stopping

    for epoch in range(epochs):
        model.train()  # Set model to training mode
        total_train_loss = 0.0

        for batch_X, batch_y in tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs} [Train]"):
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            total_train_loss += loss.item()

        # --- Validation Loop ---
        model.eval()  # Set model to evaluation mode
        total_val_loss = 0.0
        correct_predictions = 0
        total_samples = 0
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                total_val_loss += loss.item()

                # Calculate accuracy
                predicted = torch.round(torch.sigmoid(outputs))
                correct_predictions += (predicted == batch_y).sum().item()
                total_samples += batch_y.size(0)

        avg_train_loss = total_train_loss / len(train_loader)
        avg_val_loss = total_val_loss / len(val_loader)
        val_accuracy = correct_predictions / total_samples

        print(
            f"Epoch {epoch+1}: Train Loss={avg_train_loss:.4f}, Val Loss={avg_val_loss:.4f}, Val Acc={val_accuracy:.4f}"
        )

        # --- Early Stopping Logic ---
        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            patience_counter = 0
            # Optional: Save the best model
            # torch.save(model.state_dict(), 'best_model.pth')
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping triggered after {epoch+1} epochs.")
                break

    return model, best_val_accuracy


def create_features_from_pytorch_embeddings(df, trained_model):
    """
    Extracts embeddings from a trained PyTorch model and creates
    the final feature set for use in a classical ML model.
    """
    print("Extracting embeddings and creating final features...")

    # --- 1. Extract the learned embedding weights ---
    # .weight contains the lookup table. .detach().numpy() moves it from GPU/PyTorch to CPU/NumPy
    hero_embeddings_matrix = trained_model.hero_embedding.weight.detach().numpy()

    features_list = []

    # --- 2. Loop through the DataFrame to create features for each match ---
    for _, row in df.iterrows():
        picks = row["hero_picks"]

        # Look up the learned embeddings for each hero
        # Note: We index directly into the matrix
        radiant_embeddings = hero_embeddings_matrix[picks[:5]]
        dire_embeddings = hero_embeddings_matrix[picks[5:]]

        # --- 3. Calculate features (same logic as your Keras .create_features method) ---
        radiant_mean = np.mean(radiant_embeddings, axis=0)
        dire_mean = np.mean(dire_embeddings, axis=0)

        features = {
            "match_id": row["match_id"],
            # Team averages
            **{f"radiant_mean_{i}": val for i, val in enumerate(radiant_mean)},
            **{f"dire_mean_{i}": val for i, val in enumerate(dire_mean)},
            # Difference (most important)
            **{f"diff_{i}": val for i, val in enumerate(radiant_mean - dire_mean)},
            # Interaction
            **{f"mult_{i}": val for i, val in enumerate(radiant_mean * dire_mean)},
            # Team diversity
            "radiant_std": np.mean(np.std(radiant_embeddings, axis=0)),
            "dire_std": np.mean(np.std(dire_embeddings, axis=0)),
            # Similarity
            "cosine_sim": np.dot(radiant_mean, dire_mean)
            / (np.linalg.norm(radiant_mean) * np.linalg.norm(dire_mean) + 1e-8),
        }
        features_list.append(features)

    return pd.DataFrame(features_list)


# --- EXAMPLE USAGE ---

# 1. Train the model and get the final trained instance
# trained_pytorch_model, final_accuracy = train_pytorch_model(
#     hero_with_outcome_df,
#     n_heroes=150,
#     embedding_dim=32
# )
# print(f"\nBest validation accuracy: {final_accuracy:.4f}")

# 2. (Optional) Extract the learned embeddings
# hero_embeddings_from_pytorch = trained_pytorch_model.hero_embedding.weight.detach().numpy()
# print(f"Extracted PyTorch embeddings with shape: {hero_embeddings_from_pytorch.shape}")
