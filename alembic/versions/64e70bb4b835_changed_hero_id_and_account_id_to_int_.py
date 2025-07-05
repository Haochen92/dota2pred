"""Changed IDs to int/BigInt, datetime cols to timestamptz, adjust match_predictions

Revision ID: <your_new_revision_id_after_this_edit> # Update this
Revises: 6f1ee7bbbedb # Or your actual previous revision
Create Date: <timestamp>

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "64e70bb4b835"
down_revision: Union[str, None] = "6f1ee7bbbedb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def id_float_to_int_pg_using(column_name: str, target_type: str = "integer") -> str:
    """
    Helper to create postgresql_using clause for converting float IDs (double precision)
    to integer or bigint, handling NULL, NaN, and Infinity.
    """
    return f"""
    CASE
        WHEN {column_name} IS NULL THEN NULL
        WHEN {column_name} = 'NaN'::double precision THEN NULL
        WHEN {column_name} = 'Infinity'::double precision THEN NULL
        WHEN {column_name} = '-Infinity'::double precision THEN NULL
        WHEN TRUNC({column_name}) > {'9223372036854775807' if target_type == 'bigint' else '2147483647'} THEN NULL -- Or a default error/sentinel ID
        WHEN TRUNC({column_name}) < {'-9223372036854775808' if target_type == 'bigint' else '-2147483648'} THEN NULL -- Or a default error/sentinel ID
        ELSE TRUNC({column_name})::{target_type}
    END
    """


def upgrade() -> None:
    # ### Manually adjusted Alembic commands ###

    # --- Step 1: Drop Foreign Keys that might be affected by type changes ---
    op.drop_constraint("match_outcomes_match_id_fkey", "match_outcomes", type_="foreignkey")
    op.drop_constraint("match_predictions_match_id_fkey", "match_predictions", type_="foreignkey")
    # Add other FK drops here if TeamHistoryTable, etc., have FKs to matches.match_id

    # --- Step 2: Modify 'match_predictions' table ---
    # Add new columns as nullable first, then update, then set NOT NULL
    op.add_column("match_predictions", sa.Column("predictor_name", sa.String(), nullable=True))
    op.execute("UPDATE match_predictions SET predictor_name = 'UnknownPredictor' WHERE predictor_name IS NULL")
    op.alter_column("match_predictions", "predictor_name", nullable=False)

    op.add_column("match_predictions", sa.Column("predictor_version", sa.String(), nullable=True))
    op.execute("UPDATE match_predictions SET predictor_version = '0.0.0' WHERE predictor_version IS NULL")
    op.alter_column("match_predictions", "predictor_version", nullable=False)

    # Alter prediction_probability to be nullable (assuming it was NOT NULL Float)
    # If it's changing type from Float to Boolean (Optional[bool]), that's a different migration.
    # Assuming it remains Float but becomes nullable.
    op.add_column("match_predictions", sa.Column("prediction_probability", sa.Float(), nullable=True))

    op.alter_column(
        "match_predictions",
        "prediction_date",
        existing_type=postgresql.TIMESTAMP(),  # Naive timestamp
        type_=sa.TIMESTAMP(timezone=True),  # Becomes TIMESTAMPTZ
        nullable=True,  # Assuming your model makes this Optional[datetime]
        postgresql_using="prediction_date AT TIME ZONE 'UTC'",
    )  # Assume existing naive were UTC

    op.create_index(
        op.f("ix_match_predictions_prediction_date"),
        "match_predictions",
        ["prediction_date"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_match_predictions_predictor_name"),
        "match_predictions",
        ["predictor_name"],
        unique=False,
        if_not_exists=True,
    )

    op.drop_column("match_predictions", "version")
    op.drop_column("match_predictions", "name")

    # --- Step 3: Modify 'matches' table ---
    hero_id_slots = ["0", "1", "2", "3", "4", "128", "129", "130", "131", "132"]
    for slot in hero_id_slots:
        op.alter_column(
            "matches",
            f"slot_{slot}_hero_id",
            existing_type=sa.DOUBLE_PRECISION(precision=53),
            type_=sa.Integer(),
            existing_nullable=True,
            postgresql_using=id_float_to_int_pg_using(f"slot_{slot}_hero_id", "integer"),
        )

    account_id_slots = hero_id_slots  # Same slots for account IDs
    for slot in account_id_slots:
        op.alter_column(
            "matches",
            f"slot_{slot}_account_id",
            existing_type=sa.DOUBLE_PRECISION(precision=53),
            type_=sa.BigInteger(),
            existing_nullable=True,
            postgresql_using=id_float_to_int_pg_using(f"slot_{slot}_account_id", "bigint"),
        )

    op.alter_column(
        "matches",
        "radiant_team_id",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using=id_float_to_int_pg_using("radiant_team_id", "bigint"),
    )
    op.alter_column(
        "matches",
        "dire_team_id",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using=id_float_to_int_pg_using("dire_team_id", "bigint"),
    )

    op.alter_column(
        "matches",
        "start_time",
        existing_type=sa.DOUBLE_PRECISION(precision=53),  # Assuming it was float (epoch seconds)
        type_=sa.TIMESTAMP(timezone=True),
        existing_nullable=True,
        postgresql_using="to_timestamp(start_time)",
    )

    # --- Step 4: Modify other history tables ('win' and 'start_time') ---
    history_tables = ["player_hero_histories", "team_histories", "team_matchup_histories"]
    for table_name in history_tables:
        # Make 'win' column nullable if it wasn't
        op.alter_column(
            table_name, "win", existing_type=sa.BOOLEAN(), nullable=True
        )  # Consistent with Optional[bool] in model

        # Convert 'start_time' from float (epoch) to TIMESTAMPTZ
        op.alter_column(
            table_name,
            "start_time",
            existing_type=sa.DOUBLE_PRECISION(precision=53),
            type_=sa.TIMESTAMP(timezone=True),
            nullable=True,  # Consistent with Optional[datetime]
            postgresql_using="to_timestamp(start_time)",
        )

    # --- Step 5: Recreate Foreign Keys ---
    # Ensure column types for FKs are now compatible.
    # matches.match_id is BigInteger, so referencing columns should be BigInteger.
    op.create_foreign_key(
        "fk_match_outcomes_match_id",  # Choose a consistent name
        "match_outcomes",
        "matches",
        ["match_id"],
        ["match_id"],  # Assuming match_outcomes.match_id is also BigInt now
    )
    op.create_foreign_key(
        "fk_match_predictions_match_id",
        "match_predictions",
        "matches",
        ["match_id"],
        ["match_id"],  # Assuming match_predictions.match_id is also BigInt
    )
    # Add FK creations for TeamHistoryTable, etc. if they reference matches.match_id
    # op.create_foreign_key("fk_team_histories_match_id", "team_histories", "matches", ["match_id"], ["match_id"])
    # op.create_foreign_key("fk_player_hero_histories_match_id", "player_hero_histories", "matches", ["match_id"], ["match_id"])
    # op.create_foreign_key("fk_team_matchup_histories_match_id", "team_matchup_histories", "matches", ["match_id"], ["match_id"])

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### Manually adjusted Alembic commands (reverse of upgrade) ###

    # --- Step 1 (Reverse of Upgrade Step 5): Drop Foreign Keys created in upgrade ---
    op.drop_constraint("fk_match_predictions_match_id", "match_predictions", type_="foreignkey")
    op.drop_constraint("fk_match_outcomes_match_id", "match_outcomes", type_="foreignkey")
    # op.drop_constraint("fk_team_matchup_histories_match_id", "team_matchup_histories", type_='foreignkey')
    # op.drop_constraint("fk_player_hero_histories_match_id", "player_hero_histories", type_='foreignkey')
    # op.drop_constraint("fk_team_histories_match_id", "team_histories", type_='foreignkey')

    # --- Step 2 (Reverse of Upgrade Step 4): Modify other history tables ---
    history_tables = ["player_hero_histories", "team_histories", "team_matchup_histories"]
    for table_name in reversed(history_tables):  # Process in reverse for downgrade
        op.alter_column(
            table_name,
            "start_time",
            existing_type=sa.TIMESTAMP(timezone=True),
            type_=sa.DOUBLE_PRECISION(precision=53),
            nullable=True,  # Keep new nullability
            postgresql_using="extract(epoch from start_time)",
        )
        op.alter_column(
            table_name, "win", existing_type=sa.BOOLEAN(), nullable=False
        )  # IMPORTANT: Revert to original nullability. If it was NOT NULL, set False.
        # If it was always nullable, this is fine. Check original schema!

    # --- Step 3 (Reverse of Upgrade Step 3): Modify 'matches' table ---
    op.alter_column(
        "matches",
        "start_time",
        existing_type=sa.TIMESTAMP(timezone=True),
        type_=sa.DOUBLE_PRECISION(precision=53),
        existing_nullable=True,  # Retain original nullability
        postgresql_using="extract(epoch from start_time)",
    )

    op.alter_column(
        "matches",
        "dire_team_id",
        existing_type=sa.BigInteger(),
        type_=sa.DOUBLE_PRECISION(precision=53),
        existing_nullable=True,
        postgresql_using="dire_team_id::double precision",
    )
    op.alter_column(
        "matches",
        "radiant_team_id",
        existing_type=sa.BigInteger(),
        type_=sa.DOUBLE_PRECISION(precision=53),
        existing_nullable=True,
        postgresql_using="radiant_team_id::double precision",
    )

    account_id_slots = ["0", "1", "2", "3", "4", "128", "129", "130", "131", "132"]
    for slot in reversed(account_id_slots):
        op.alter_column(
            "matches",
            f"slot_{slot}_account_id",
            existing_type=sa.BigInteger(),
            type_=sa.DOUBLE_PRECISION(precision=53),
            existing_nullable=True,
            postgresql_using=f"slot_{slot}_account_id::double precision",
        )

    hero_id_slots = account_id_slots
    for slot in reversed(hero_id_slots):
        op.alter_column(
            "matches",
            f"slot_{slot}_hero_id",
            existing_type=sa.Integer(),
            type_=sa.DOUBLE_PRECISION(precision=53),
            existing_nullable=True,
            postgresql_using=f"slot_{slot}_hero_id::double precision",
        )

    # --- Step 4 (Reverse of Upgrade Step 2): Modify 'match_predictions' table ---
    op.add_column(
        "match_predictions", sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=True)
    )  # Assuming VARCHAR & nullable
    op.add_column(
        "match_predictions", sa.Column("version", sa.VARCHAR(), autoincrement=False, nullable=True)
    )  # Assuming VARCHAR & nullable

    op.drop_index(op.f("ix_match_predictions_predictor_name"), table_name="match_predictions")
    op.drop_index(op.f("ix_match_predictions_prediction_date"), table_name="match_predictions")

    op.alter_column(
        "match_predictions",
        "prediction_date",
        existing_type=sa.TIMESTAMP(timezone=True),
        type_=postgresql.TIMESTAMP(),  # Revert to naive timestamp
        nullable=False,  # IMPORTANT: Revert to original nullability (assuming NOT NULL)
        postgresql_using="prediction_date AT TIME ZONE 'UTC'",
    )  # Get naive representation of UTC moment

    op.drop_column("match_predictions", "predictor_version")
    op.drop_column("match_predictions", "predictor_name")

    # --- Step 5 (Reverse of Upgrade Step 1): Recreate original Foreign Keys ---
    # Use the original constraint names and definitions
    op.create_foreign_key(
        "match_predictions_match_id_fkey",  # Original name
        "match_predictions",
        "matches",
        ["match_id"],
        ["match_id"],
        # Add ondelete/onupdate if they existed
    )
    op.create_foreign_key(
        "match_outcomes_match_id_fkey", "match_outcomes", "matches", ["match_id"], ["match_id"]  # Original name
    )
    # ### end Alembic commands ###
