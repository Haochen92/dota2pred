from datetime import datetime, timezone

from dota_oracle_common.models.odds import MatchOddsSnapshotTable
from live_orchestrator_app.scripts.paper_bet_replay import BetConfig, full_kelly_fraction, evaluate_bet


def _snap(a_bid=0.58, a_ask=0.60, a_liq=50_000, b_bid=0.38, b_ask=0.40, b_liq=50_000) -> MatchOddsSnapshotTable:
    return MatchOddsSnapshotTable(
        match_id=1,
        snapshot_kind="entry",
        captured_at=datetime.now(timezone.utc),
        a_best_bid=a_bid,
        a_best_ask=a_ask,
        a_liquidity=a_liq,
        b_best_bid=b_bid,
        b_best_ask=b_ask,
        b_liquidity=b_liq,
    )


def test_full_kelly_fraction() -> None:
    assert full_kelly_fraction(0.6, 0.5) == (0.6 - 0.5) / (1 - 0.5)
    assert full_kelly_fraction(0.5, 0.6) == 0.0  # no edge
    assert full_kelly_fraction(0.6, 0.0) == 0.0  # degenerate price
    assert full_kelly_fraction(0.6, 1.0) == 0.0


def test_evaluate_bet_takes_positive_edge_side() -> None:
    # Model thinks radiant wins 70%; radiant ask 0.60 -> edge 0.10 > tau.
    decision, skip = evaluate_bet(0.70, _snap(), BetConfig(tau=0.03))
    assert skip is None
    assert decision["side"] == "radiant"
    assert round(decision["edge"], 4) == 0.10


def test_evaluate_bet_below_threshold_skips() -> None:
    # radiant ask 0.60, model 0.61 -> edge 0.01 < tau 0.03; dire edge negative.
    decision, skip = evaluate_bet(0.61, _snap(), BetConfig(tau=0.03))
    assert decision is None
    assert skip == "edge_below_threshold"


def test_evaluate_bet_thin_market_skips() -> None:
    decision, skip = evaluate_bet(0.70, _snap(a_liq=100, b_liq=100), BetConfig(min_liquidity=500))
    assert decision is None
    assert skip == "market_too_thin"


def test_evaluate_bet_wide_spread_skips() -> None:
    decision, skip = evaluate_bet(
        0.70, _snap(a_bid=0.40, a_ask=0.60, b_bid=0.40, b_ask=0.60), BetConfig(max_spread=0.06)
    )
    assert decision is None
    assert skip == "spread_too_wide"


def test_evaluate_bet_picks_dire_when_thats_the_edge() -> None:
    # Model thinks radiant only 25% -> dire 75%; dire ask 0.40 -> edge 0.35.
    decision, skip = evaluate_bet(0.25, _snap(), BetConfig(tau=0.03))
    assert skip is None
    assert decision["side"] == "dire"
