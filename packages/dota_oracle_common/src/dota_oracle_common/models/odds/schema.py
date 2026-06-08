from enum import Enum
from datetime import datetime
from typing import Optional, Any, Dict

from pydantic import BaseModel


class SnapshotKind(str, Enum):
    """When, relative to the match, a snapshot was taken.

    Only ENTRY (at draft-lock / prediction time) is captured today. CLOSING (near game start,
    for CLV) is reserved for a later iteration -- see docs/2026-06-08-polymarket-odds-capture.md.
    """

    ENTRY = "entry"
    CLOSING = "closing"


class OddsSkipReason(str, Enum):
    """Why a prediction did not produce a tradeable snapshot. Recorded, not dropped silently --
    the skip-rate is itself a feasibility metric."""

    NO_MARKET_FOUND = "no_market_found"
    MARKET_TOO_THIN = "market_too_thin"
    SPREAD_TOO_WIDE = "spread_too_wide"


class SideQuote(BaseModel):
    """One outcome token's price picture."""

    token_id: str
    best_bid: float
    best_ask: float
    liquidity: float


class ResolvedMarket(BaseModel):
    """Output of the match->market join: the Polymarket market for a match plus the per-side
    outcome tokens, already oriented radiant/dire. The join is the documented main source of
    silent failures, so it is isolated in this one DTO."""

    event_slug: Optional[str] = None
    market_slug: Optional[str] = None
    condition_id: Optional[str] = None
    token_id_radiant: str
    token_id_dire: str
    raw_market: Optional[Dict[str, Any]] = None


class MarketSnapshot(BaseModel):
    """Both sides of a match's market at one instant, as resolved by the Polymarket client.
    Side A = radiant, side B = dire."""

    event_slug: Optional[str] = None
    market_slug: Optional[str] = None
    condition_id: Optional[str] = None
    side_a: SideQuote
    side_b: SideQuote
    raw: Optional[Dict[str, Any]] = None


class OddsResultPayload(BaseModel):
    """In-memory work item produced by the odds data provider and consumed by the processor.

    Carries either a resolved snapshot or a skip_reason. Unlike the stream payloads this never
    crosses Redis -- it is built and consumed within a single cycle (the same pattern as
    CompletedMatchPayload). The processor maps it onto MatchOddsSnapshotTable.
    """

    match_id: int
    snapshot_kind: SnapshotKind = SnapshotKind.ENTRY
    captured_at: datetime
    game_time_seconds: Optional[int] = None
    provider: str = "polymarket"

    # Market identity
    event_slug: Optional[str] = None
    market_slug: Optional[str] = None
    condition_id: Optional[str] = None
    token_id_a: Optional[str] = None
    token_id_b: Optional[str] = None

    # Side A = radiant, side B = dire
    a_best_bid: Optional[float] = None
    a_best_ask: Optional[float] = None
    a_liquidity: Optional[float] = None
    b_best_bid: Optional[float] = None
    b_best_ask: Optional[float] = None
    b_liquidity: Optional[float] = None

    skip_reason: Optional[OddsSkipReason] = None
    raw: Optional[Dict[str, Any]] = None
