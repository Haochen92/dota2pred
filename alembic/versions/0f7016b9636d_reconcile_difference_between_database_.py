"""reconcile difference between database and model table

Revision ID: 0f7016b9636d
Revises: f6a389595e8f
Create Date: 2025-08-02 07:05:06.260365

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0f7016b9636d"
down_revision: Union[str, None] = "f6a389595e8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drops incorrect single-column PKs and creates the correct composite PKs.
    Note: player_hero_histories had no PK, so we only need to create one.
    """
    # --- Fix for team_histories ---
    print("Fixing primary key for team_histories...")
    op.drop_constraint("team_histories_pkey", "team_histories", type_="primary")
    op.create_primary_key("team_histories_pkey", "team_histories", ["team_name", "match_id"])

    # --- Fix for player_hero_histories ---
    print("Creating primary key for player_hero_histories...")
    # This table has no primary key, so we just create one. No drop needed.
    op.create_primary_key("player_hero_histories_pkey", "player_hero_histories", ["account_id", "hero_id", "match_id"])

    # --- Fix for match_predictions ---
    print("Fixing primary key for match_predictions...")
    op.drop_constraint("match_predictions_pkey", "match_predictions", type_="primary")
    op.create_primary_key("match_predictions_pkey", "match_predictions", ["match_id", "predictor_name"])


def downgrade() -> None:
    """
    Reverts the changes, restoring the old (and incorrect) schema.
    """
    # --- Revert for match_predictions ---
    print("Reverting primary key for match_predictions...")
    op.drop_constraint("match_predictions_pkey", "match_predictions", type_="primary")
    op.create_primary_key("match_predictions_pkey", "match_predictions", ["match_id"])

    # --- Revert for player_hero_histories ---
    print("Reverting primary key for player_hero_histories...")
    # To revert, we just drop the PK we added, as there was none before.
    op.drop_constraint("player_hero_histories_pkey", "player_hero_histories", type_="primary")

    # --- Revert for team_histories ---
    print("Reverting primary key for team_histories...")
    op.drop_constraint("team_histories_pkey", "team_histories", type_="primary")
    op.create_primary_key("team_histories_pkey", "team_histories", ["team_name"])
