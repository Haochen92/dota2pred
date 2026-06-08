"""Offline paper-betting replay over captured Polymarket snapshots.

Joins match_odds_snapshots (entry, with a captured market) + match_predictions + match_outcomes and
replays the decision/sizing rule, writing one match_paper_bets row per (match_id, predictor_name)
and printing a per-predictor report (hit rate, ROI, Brier, compounding vs flat bankroll).

FORWARD-ONLY, by necessity: a finished game's draft-time line is unrecoverable (its Polymarket
market resolves -> the order book 404s and prices-history returns empty), so this can only replay
snapshots captured live, going forward -- it is NOT a historical backtest. With no captured
snapshots yet it prints an empty report.

Decision/sizing logic reproduces the betting_poc.py spec (per-side EV vs the ask, threshold tau,
liquidity+spread gate, fractional Kelly, flat-stake baseline); that reference file is left untouched.

Assumption: match_predictions.prediction_probability is P(radiant win). If the model ever stores
confidence-of-predicted-class instead, flip p_radiant accordingly (see _p_radiant).
"""

import argparse
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from prefect import flow
from sqlmodel import select

from dota_oracle_common.models.inference import MatchPredictionTable
from dota_oracle_common.models.match import MatchOutcomeTable
from dota_oracle_common.models.odds import MatchOddsSnapshotTable, MatchPaperBetTable
from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.repositories.odds_repository import OddsRepository
from dota_oracle_common.utils import get_logger
from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Engine (pure logic; betting_poc.py is the spec)
# --------------------------------------------------------------------------- #


@dataclass
class BetConfig:
    tau: float = 0.03  # min edge (q_side - ask_side) to bet
    kelly_fraction: float = 0.25  # fraction of full Kelly
    min_liquidity: float = 500.0  # skip thin markets
    max_spread: float = 0.06  # skip markets whose spread eats the edge
    flat_stake_pct: float = 0.01  # baseline: 1% of starting bankroll per bet


def full_kelly_fraction(q: float, p: float) -> float:
    """Fraction of bankroll to stake for a $1 binary bought at price p with win prob q:
    f* = (q - p) / (1 - p). Zero for non-positive edge or degenerate prices."""
    if not (0.0 < p < 1.0) or q <= p:
        return 0.0
    return (q - p) / (1.0 - p)


def evaluate_bet(
    p_radiant: float, snap: MatchOddsSnapshotTable, cfg: BetConfig
) -> Tuple[Optional[dict], Optional[str]]:
    """Per-side EV against the ask actually paid. Returns (decision, None) or (None, skip_reason)."""
    sides = [
        ("radiant", p_radiant, snap.a_best_ask, snap.a_best_bid, snap.a_liquidity),
        ("dire", 1.0 - p_radiant, snap.b_best_ask, snap.b_best_bid, snap.b_liquidity),
    ]
    tradeable = []
    for side, q, ask, bid, liq in sides:
        if ask is None or bid is None:
            continue
        if liq is not None and liq < cfg.min_liquidity:
            continue
        if (ask - bid) > cfg.max_spread:
            continue
        tradeable.append((side, q, ask))

    if not tradeable:
        thin = any(liq is not None and liq < cfg.min_liquidity for _, _, _, _, liq in sides)
        return None, ("market_too_thin" if thin else "spread_too_wide")

    side, q, ask = max(tradeable, key=lambda s: s[1] - s[2])
    edge = q - ask
    if edge <= cfg.tau:
        return None, "edge_below_threshold"
    return {"side": side, "q": q, "ask": ask, "edge": edge}, None


# --------------------------------------------------------------------------- #
# Replay
# --------------------------------------------------------------------------- #


def _p_radiant(pred: MatchPredictionTable) -> Optional[float]:
    """P(radiant win) from a stored prediction. Assumes prediction_probability is P(radiant win)."""
    return None if pred.prediction_probability is None else float(pred.prediction_probability)


async def _load(session, predictor_name: Optional[str]):
    odds_repo = OddsRepository(session=session)
    snapshots = await odds_repo.get_entry_snapshots_with_prices()
    match_ids = [s.match_id for s in snapshots]
    if not match_ids:
        return snapshots, {}, {}

    pred_stmt = select(MatchPredictionTable).where(MatchPredictionTable.match_id.in_(match_ids))  # type: ignore[attr-defined]
    if predictor_name:
        pred_stmt = pred_stmt.where(MatchPredictionTable.predictor_name == predictor_name)
    preds = (await session.execute(pred_stmt)).scalars().all()
    preds_by_predictor: Dict[str, Dict[int, MatchPredictionTable]] = {}
    for p in preds:
        preds_by_predictor.setdefault(p.predictor_name, {})[p.match_id] = p

    out_stmt = select(MatchOutcomeTable).where(MatchOutcomeTable.match_id.in_(match_ids))  # type: ignore[attr-defined]
    outcomes = {o.match_id: o.radiant_win for o in (await session.execute(out_stmt)).scalars().all()}
    return snapshots, preds_by_predictor, outcomes


def _replay_predictor(
    predictor_name: str,
    snapshots: List[MatchOddsSnapshotTable],
    preds: Dict[int, MatchPredictionTable],
    outcomes: Dict[int, bool],
    cfg: BetConfig,
    starting_bankroll: float,
    replayed_at,
) -> Tuple[List[MatchPaperBetTable], dict]:
    """Replay one predictor over the snapshots in capture order, compounding the bankroll."""
    bankroll = starting_bankroll
    flat_bankroll = starting_bankroll
    rows: List[MatchPaperBetTable] = []
    brier_terms: List[float] = []
    pnls: List[float] = []
    staked = 0.0
    wins = 0
    n_bets = 0

    for snap in snapshots:
        pred = preds.get(snap.match_id)
        if pred is None:
            continue
        p_rad = _p_radiant(pred)
        winner = None
        if snap.match_id in outcomes:
            winner = "radiant" if outcomes[snap.match_id] else "dire"
            if p_rad is not None:
                brier_terms.append((p_rad - (1.0 if outcomes[snap.match_id] else 0.0)) ** 2)

        row = MatchPaperBetTable(
            match_id=snap.match_id,
            predictor_name=predictor_name,
            winner=winner,
            config_tau=cfg.tau,
            config_kelly_fraction=cfg.kelly_fraction,
            replayed_at=replayed_at,
        )

        if p_rad is None:
            row.skip_reason = "no_model_probability"
            rows.append(row)
            continue

        decision, skip_reason = evaluate_bet(p_rad, snap, cfg)
        if decision is None:
            row.skip_reason = skip_reason
            rows.append(row)
            continue

        price = decision["ask"]
        stake = round(bankroll * full_kelly_fraction(decision["q"], price) * cfg.kelly_fraction, 6)
        flat_stake = round(starting_bankroll * cfg.flat_stake_pct, 6)
        shares = round(stake / price, 6) if price > 0 else 0.0
        row.bet_side = decision["side"]
        row.model_p = decision["q"]
        row.entry_price = price
        row.edge = decision["edge"]
        row.stake = stake
        row.shares = shares
        row.flat_stake = flat_stake
        n_bets += 1
        staked += stake

        if winner is not None:
            won = winner == decision["side"]
            row.pnl = round(shares * (1.0 - price), 6) if won else round(-stake, 6)
            flat_shares = flat_stake / price if price > 0 else 0.0
            row.flat_pnl = round(flat_shares * (1.0 - price), 6) if won else round(-flat_stake, 6)
            bankroll = round(bankroll + row.pnl, 6)
            flat_bankroll = round(flat_bankroll + row.flat_pnl, 6)
            pnls.append(row.pnl)
            wins += won
        rows.append(row)

    settled = len(pnls)
    report = {
        "predictor": predictor_name,
        "snapshots": len(snapshots),
        "n_bets": n_bets,
        "n_settled": settled,
        "hit_rate": round(wins / settled, 4) if settled else None,
        "total_staked": round(staked, 2),
        "pnl": round(sum(pnls), 2) if pnls else 0.0,
        "roi": round(sum(pnls) / staked, 4) if staked else None,
        "brier": round(sum(brier_terms) / len(brier_terms), 5) if brier_terms else None,
        "final_bankroll_kelly": round(bankroll, 2),
        "final_bankroll_flat": round(flat_bankroll, 2),
    }
    return rows, report


async def run_replay(predictor_name: Optional[str], cfg: BetConfig, starting_bankroll: float) -> List[dict]:
    replayed_at = get_current_utc_iso_timestamp()
    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        snapshots, preds_by_predictor, outcomes = await _load(session, predictor_name)

        if not snapshots:
            logger.info("No captured entry snapshots yet; nothing to replay (this is forward-only).")
            return []
        if not preds_by_predictor:
            logger.info(f"{len(snapshots)} snapshots but no matching predictions; nothing to replay.")
            return []

        reports = []
        all_rows: List[MatchPaperBetTable] = []
        for name, preds in preds_by_predictor.items():
            rows, report = _replay_predictor(name, snapshots, preds, outcomes, cfg, starting_bankroll, replayed_at)
            all_rows.extend(rows)
            reports.append(report)

        async with session.begin():
            await OddsRepository(session=session).upsert_paper_bets(all_rows)

    for r in reports:
        _print_report(r)
    return reports


def _print_report(r: dict) -> None:
    print(f"\n=== paper-bet replay: {r['predictor']} ===")
    print(f"  snapshots replayed : {r['snapshots']}")
    print(f"  bets placed        : {r['n_bets']}  (settled {r['n_settled']})")
    if r["hit_rate"] is not None:
        print(f"  hit rate           : {r['hit_rate']:.1%}")
    print(f"  total staked       : ${r['total_staked']:,.2f}")
    if r["roi"] is not None:
        print(f"  PnL                : ${r['pnl']:,.2f}  (ROI {r['roi']:.2%})")
    if r["brier"] is not None:
        print(f"  Brier              : {r['brier']:.4f}")
    print(f"  bankroll Kelly     : ${r['final_bankroll_kelly']:,.2f}  (flat ${r['final_bankroll_flat']:,.2f})")


@flow(name="paper_bet_replay")
async def paper_bet_replay_flow(
    predictor: Optional[str] = None,
    tau: float = 0.03,
    kelly_fraction: float = 0.25,
    bankroll: float = 1000.0,
) -> List[dict]:
    """Scheduled entry point. Re-runs the replay (idempotent) so newly-settled outcomes get picked
    up; defaults replay all predictors. Logs a one-line summary per predictor for Loki/Prefect."""
    cfg = BetConfig(tau=tau, kelly_fraction=kelly_fraction)
    reports = await run_replay(predictor_name=predictor, cfg=cfg, starting_bankroll=bankroll)
    for r in reports:
        logger.info(
            f"paper_bet_replay[{r['predictor']}]: bets={r['n_bets']} settled={r['n_settled']} "
            f"pnl={r['pnl']} roi={r['roi']} brier={r['brier']} bankroll={r['final_bankroll_kelly']}"
        )
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline paper-betting replay over captured odds snapshots.")
    parser.add_argument("--predictor", default=None, help="Limit to one predictor_name (default: all present).")
    parser.add_argument("--tau", type=float, default=0.03, help="Min edge to bet.")
    parser.add_argument("--kelly-fraction", type=float, default=0.25, help="Fraction of full Kelly.")
    parser.add_argument("--bankroll", type=float, default=1000.0, help="Starting bankroll.")
    args = parser.parse_args()

    cfg = BetConfig(tau=args.tau, kelly_fraction=args.kelly_fraction)
    asyncio.run(run_replay(predictor_name=args.predictor, cfg=cfg, starting_bankroll=args.bankroll))


if __name__ == "__main__":
    main()
