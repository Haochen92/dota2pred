"""add match_paper_bets table (offline paper-betting replay results)

Revision ID: 0b57bea70dd5
Revises: 0dd5feed0a11
Create Date: 2026-06-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0b57bea70dd5"
down_revision: Union[str, None] = "0dd5feed0a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COMMENT = (
    "Offline paper-betting replay results per (match_id, predictor_name): the bet the engine would "
    "have made against the captured Polymarket snapshot, its CLV and settled PnL. Research artifact "
    "-- no real money, not in the live path."
)


def upgrade() -> None:
    op.create_table(
        "match_paper_bets",
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("predictor_name", sa.String(), nullable=False),
        sa.Column("bet_side", sa.String(), nullable=True),
        sa.Column("model_p", sa.Float(), nullable=True),
        sa.Column("entry_price", sa.Float(), nullable=True),
        sa.Column("edge", sa.Float(), nullable=True),
        sa.Column("stake", sa.Float(), nullable=True),
        sa.Column("shares", sa.Float(), nullable=True),
        sa.Column("flat_stake", sa.Float(), nullable=True),
        sa.Column("skip_reason", sa.String(), nullable=True),
        sa.Column("closing_price", sa.Float(), nullable=True),
        sa.Column("clv", sa.Float(), nullable=True),
        sa.Column("winner", sa.String(), nullable=True),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("flat_pnl", sa.Float(), nullable=True),
        sa.Column("config_tau", sa.Float(), nullable=True),
        sa.Column("config_kelly_fraction", sa.Float(), nullable=True),
        sa.Column("replayed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.match_id"]),
        sa.PrimaryKeyConstraint("match_id", "predictor_name"),
        comment=_COMMENT,
    )


def downgrade() -> None:
    op.drop_table("match_paper_bets")
