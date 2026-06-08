from typing import Optional, Any, Dict
from datetime import datetime

from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column, TIMESTAMP, ForeignKey, String, Float, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB


class MatchOddsSnapshotTable(SQLModel, table=True):
    """Polymarket order-book snapshot for a pro match, captured at draft-lock.

    Market-only and predictor-independent (the market is the market). The composite key allows
    more than one snapshot per game -- today only ``entry`` is written; ``closing`` (for CLV) is a
    future addition. Decisions/PnL live in a separate offline-replay table, not here.

    Side A = radiant, side B = dire (aligned with MatchTable's radiant_team_id / dire_team_id).
    """

    __tablename__ = "match_odds_snapshots"
    __table_args__ = {
        "comment": (
            "Polymarket order-book snapshots for pro matches, captured at draft-lock for "
            "paper-betting feasibility analysis. Market-only and predictor-independent; one row "
            "per (match_id, snapshot_kind). Decisions/PnL live in a separate offline-replay table."
        )
    }

    # Composite primary key: one game (match_id) x snapshot_kind.
    match_id: int = Field(sa_column=Column(BigInteger, ForeignKey("matches.match_id"), primary_key=True))
    snapshot_kind: str = Field(sa_column=Column(String, primary_key=True))

    captured_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))
    # Approx seconds since match start at capture (captured_at - matches.start_time). The
    # timing-validation field: lets offline analysis discard snapshots taken too late to be a
    # clean pre-game line.
    game_time_seconds: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))

    provider: str = Field(default="polymarket", sa_column=Column(String, nullable=False))

    # Market identity -- enough to re-pull / audit the exact market later.
    event_slug: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    market_slug: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    condition_id: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    token_id_a: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    token_id_b: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))

    a_best_bid: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    a_best_ask: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    a_liquidity: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    b_best_bid: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    b_best_ask: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    b_liquidity: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))

    # Recorded even on a skip (no market / too thin / spread too wide): the skip-rate is a
    # feasibility metric in its own right.
    skip_reason: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))

    # Verbatim provider payload, stored before interpretation so the archive survives a provider
    # or schema change.
    raw: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))


class MatchPaperBetTable(SQLModel, table=True):
    """Outcome of replaying the paper-betting engine over a stored odds snapshot.

    Populated OFFLINE (not in the live path) by joining match_odds_snapshots + match_predictions +
    match_outcomes and running the decision/sizing rule. Keyed by (match_id, predictor_name) so
    several models can be A/B'd against the same captured prices; re-running a replay overwrites the
    row (last replay wins), so the config used is recorded alongside.
    """

    __tablename__ = "match_paper_bets"
    __table_args__ = {
        "comment": (
            "Offline paper-betting replay results per (match_id, predictor_name): the bet the engine "
            "would have made against the captured Polymarket snapshot, its CLV and settled PnL. "
            "Research artifact -- no real money, not in the live path."
        )
    }

    match_id: int = Field(sa_column=Column(BigInteger, ForeignKey("matches.match_id"), primary_key=True))
    predictor_name: str = Field(sa_column=Column(String, primary_key=True))

    # Decision (None on skip)
    bet_side: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))  # "radiant" / "dire"
    model_p: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))  # model prob for bet side
    entry_price: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))  # ask paid
    edge: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    stake: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    shares: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    flat_stake: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    skip_reason: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))

    # Closing line value (None until a closing snapshot exists -- v1 captures entry only)
    closing_price: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    clv: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))

    # Settlement
    winner: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))  # "radiant" / "dire"
    pnl: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    flat_pnl: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))

    # The config that produced this row (a replay is config-dependent) + when it ran.
    config_tau: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    config_kelly_fraction: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    replayed_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))


class PolymarketTeamMapTable(SQLModel, table=True):
    """Bridge from a Steam/OpenDota team_id (what we have at prediction time) to a Polymarket
    team slug (how Polymarket keys its markets -- it carries no Steam id). Seeded and maintained
    by hand; the resolver reads it and logs a WARN for any unmapped team so the map can grow."""

    __tablename__ = "polymarket_team_map"
    __table_args__ = {
        "comment": (
            "Bridge from a Steam/OpenDota team_id (known at prediction time) to a Polymarket team "
            "slug (how Polymarket keys its markets -- it carries no Steam id). Seeded and "
            "maintained by hand; used to join pro matches to Polymarket markets."
        )
    }

    steam_team_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    polymarket_slug: str = Field(sa_column=Column(String, nullable=False))
    canonical_name: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    # False until a human has confirmed the slug resolves to the right team on Polymarket.
    verified: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))
    updated_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))
