# In alembic/versions/0cde92c12e49_....py

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0cde92c12e49"
down_revision: Union[str, None] = "ae330bf4787a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Manually adjusted migration to change PK from team_name to team_id ###

    # --- Step 1: Add the new columns as NULLABLE to start ---
    op.add_column("team_decayed_states", sa.Column("team_id", sa.BigInteger(), nullable=True))
    op.add_column("team_matchup_decayed_states", sa.Column("team1_id", sa.BigInteger(), nullable=True))
    op.add_column("team_matchup_decayed_states", sa.Column("team2_id", sa.BigInteger(), nullable=True))

    # --- Step 2: Populate the new columns with data from the matches table ---
    # This assumes you have team IDs in your 'matches' table. Adjust if the source is different.
    op.execute(
        """
        UPDATE team_decayed_states tds
        SET team_id = m.radiant_team_id
        FROM matches m
        WHERE tds.match_id = m.match_id AND tds.team_name = m.radiant_name;
    """
    )
    op.execute(
        """
        UPDATE team_decayed_states tds
        SET team_id = m.dire_team_id
        FROM matches m
        WHERE tds.match_id = m.match_id AND tds.team_name = m.dire_name;
    """
    )
    op.execute(
        """
        UPDATE team_matchup_decayed_states tmds
        SET team1_id = m.radiant_team_id, team2_id = m.dire_team_id
        FROM matches m
        WHERE tmds.match_id = m.match_id
          AND tmds.team1_name = LEAST(m.radiant_name, m.dire_name)
          AND tmds.team2_name = GREATEST(m.radiant_name, m.dire_name);
    """
    )

    # --- Step 3: Now that columns are populated, make them NOT NULL ---
    op.alter_column("team_decayed_states", "team_id", existing_type=sa.BigInteger(), nullable=False)
    op.alter_column("team_matchup_decayed_states", "team1_id", existing_type=sa.BigInteger(), nullable=False)
    op.alter_column("team_matchup_decayed_states", "team2_id", existing_type=sa.BigInteger(), nullable=False)

    # --- Step 4: Drop the old primary key constraints ---
    op.drop_constraint("team_decayed_states_pkey", "team_decayed_states", type_="primary")
    op.drop_constraint("team_matchup_decayed_states_pkey", "team_matchup_decayed_states", type_="primary")

    # --- Step 5: Create the new primary key constraints ---
    op.create_primary_key("team_decayed_states_pkey", "team_decayed_states", ["team_id", "match_id"])
    op.create_primary_key(
        "team_matchup_decayed_states_pkey", "team_matchup_decayed_states", ["team1_id", "team2_id", "match_id"]
    )

    # --- Step 6: Finally, make the old name columns nullable ---
    op.alter_column("team_decayed_states", "team_name", existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column("team_matchup_decayed_states", "team1_name", existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column("team_matchup_decayed_states", "team2_name", existing_type=sa.VARCHAR(), nullable=True)
    # ### end of manual adjustment ###


def downgrade() -> None:
    # ### Manually adjusted downgrade logic ###

    # --- Step 1: Revert name columns to be NOT NULL ---
    op.alter_column("team_decayed_states", "team_name", existing_type=sa.VARCHAR(), nullable=False)
    op.alter_column("team_matchup_decayed_states", "team1_name", existing_type=sa.VARCHAR(), nullable=False)
    op.alter_column("team_matchup_decayed_states", "team2_name", existing_type=sa.VARCHAR(), nullable=False)

    # --- Step 2: Drop the new primary key constraints ---
    op.drop_constraint("team_decayed_states_pkey", "team_decayed_states", type_="primary")
    op.drop_constraint("team_matchup_decayed_states_pkey", "team_matchup_decayed_states", type_="primary")

    # --- Step 3: Create the old primary key constraints ---
    op.create_primary_key("team_decayed_states_pkey", "team_decayed_states", ["team_name", "match_id"])
    op.create_primary_key(
        "team_matchup_decayed_states_pkey", "team_matchup_decayed_states", ["team1_name", "team2_name", "match_id"]
    )

    # --- Step 4: Drop the new id columns ---
    op.drop_column("team_decayed_states", "team_id")
    op.drop_column("team_matchup_decayed_states", "team1_id")
    op.drop_column("team_matchup_decayed_states", "team2_id")
    # ### end of manual adjustment ###
