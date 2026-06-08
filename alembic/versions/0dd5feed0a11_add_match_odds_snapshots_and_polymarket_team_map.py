"""add match_odds_snapshots and polymarket_team_map tables

Revision ID: 0dd5feed0a11
Revises: 0cde92c12e49
Create Date: 2026-06-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0dd5feed0a11"
down_revision: Union[str, None] = "0cde92c12e49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ODDS_SNAPSHOTS_COMMENT = (
    "Polymarket order-book snapshots for pro matches, captured at draft-lock for paper-betting "
    "feasibility analysis. Market-only and predictor-independent; one row per (match_id, "
    "snapshot_kind). Decisions/PnL live in a separate offline-replay table."
)
_TEAM_MAP_COMMENT = (
    "Bridge from a Steam/OpenDota team_id (known at prediction time) to a Polymarket team slug "
    "(how Polymarket keys its markets -- it carries no Steam id). Seeded and maintained by hand; "
    "used to join pro matches to Polymarket markets."
)


def upgrade() -> None:
    op.create_table(
        "match_odds_snapshots",
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("snapshot_kind", sa.String(), nullable=False),
        sa.Column("captured_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("game_time_seconds", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("event_slug", sa.String(), nullable=True),
        sa.Column("market_slug", sa.String(), nullable=True),
        sa.Column("condition_id", sa.String(), nullable=True),
        sa.Column("token_id_a", sa.String(), nullable=True),
        sa.Column("token_id_b", sa.String(), nullable=True),
        sa.Column("a_best_bid", sa.Float(), nullable=True),
        sa.Column("a_best_ask", sa.Float(), nullable=True),
        sa.Column("a_liquidity", sa.Float(), nullable=True),
        sa.Column("b_best_bid", sa.Float(), nullable=True),
        sa.Column("b_best_ask", sa.Float(), nullable=True),
        sa.Column("b_liquidity", sa.Float(), nullable=True),
        sa.Column("skip_reason", sa.String(), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.match_id"]),
        sa.PrimaryKeyConstraint("match_id", "snapshot_kind"),
        comment=_ODDS_SNAPSHOTS_COMMENT,
    )
    op.create_table(
        "polymarket_team_map",
        sa.Column("steam_team_id", sa.BigInteger(), nullable=False),
        sa.Column("polymarket_slug", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.String(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("steam_team_id"),
        comment=_TEAM_MAP_COMMENT,
    )


def downgrade() -> None:
    op.drop_table("polymarket_team_map")
    op.drop_table("match_odds_snapshots")
