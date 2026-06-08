import json
from typing import Optional, List, Dict, Any, Tuple, Iterable

import httpx

from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.odds import ResolvedMarket, MarketSnapshot, SideQuote

logger = get_logger(__name__)

# Polymarket tags each market with a sportsMarketType. The series (best-of) winner is "moneyline";
# a single-game winner is "child_moneyline" (groupItemTitle "Game N Winner"). v1 captures only the
# single-game market and only Game 1 (series 0-0) -- see docs/2026-06-08-polymarket-odds-capture.md.
GAME_WINNER_MARKET_TYPE = "child_moneyline"
DEFAULT_GAME_GROUP_TITLE = "game 1 winner"


class PolymarketClient:
    """Read-only Polymarket client for the odds-capture stage.

    Public endpoints, no auth:
      Gamma: ``{gamma}/events?tag_slug=dota-2``  -> active Dota events, each with a ``markets`` array
      CLOB:  ``{clob}/book?token_id={id}``       -> order book (bids/asks)

    The match->market join (:meth:`resolve_market`) is the part validated against the live API:
    discover Dota events, descend into each event's per-game ``child_moneyline`` market, and map the
    two outcome tokens (which carry the team display names) to radiant/dire. The HTTP layer is
    injected so this stays unit-testable without a network; a ``contract`` test exercises the live
    shapes.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        gamma_url: str,
        clob_url: str,
        tag_slug: str = "dota-2",
        game_group_title: str = DEFAULT_GAME_GROUP_TITLE,
        discovery_limit: int = 100,
    ):
        self.http = http_client
        self.gamma_url = gamma_url.rstrip("/")
        self.clob_url = clob_url.rstrip("/")
        self.tag_slug = tag_slug
        self.game_group_title = game_group_title
        self.discovery_limit = discovery_limit

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def get_market_snapshot(
        self, radiant_aliases: Iterable[str], dire_aliases: Iterable[str]
    ) -> Optional[MarketSnapshot]:
        """Resolve the per-game market for these two teams and snapshot both order books.

        Each side is a set of candidate names (the team's Steam-side name plus any
        polymarket_team_map aliases); a market matches when an outcome matches one of them. Returns
        ``None`` when no market is found (a clean, terminal no-market outcome). Network / parse
        errors propagate so the caller can decide to retry within the snapshot window.
        """
        resolved = await self.resolve_market(radiant_aliases, dire_aliases)
        if resolved is None:
            return None

        book_r = await self._fetch_book(resolved.token_id_radiant)
        book_d = await self._fetch_book(resolved.token_id_dire)
        if book_r is None or book_d is None:
            # Market resolved/closed between discovery and the book fetch -> no tradeable market.
            return None
        bid_r, ask_r, liq_r = self._best(book_r)
        bid_d, ask_d, liq_d = self._best(book_d)

        return MarketSnapshot(
            event_slug=resolved.event_slug,
            market_slug=resolved.market_slug,
            condition_id=resolved.condition_id,
            side_a=SideQuote(token_id=resolved.token_id_radiant, best_bid=bid_r, best_ask=ask_r, liquidity=liq_r),
            side_b=SideQuote(token_id=resolved.token_id_dire, best_bid=bid_d, best_ask=ask_d, liquidity=liq_d),
            raw={"market": resolved.raw_market, "book_radiant": book_r, "book_dire": book_d},
        )

    async def resolve_market(
        self, radiant_aliases: Iterable[str], dire_aliases: Iterable[str]
    ) -> Optional[ResolvedMarket]:
        """Join a match to its Polymarket per-game market and orient the tokens radiant/dire.

        Discovers active Dota events, flattens to the per-game (``child_moneyline``) Game-1 markets,
        and returns the first whose two outcomes map to both of our teams (matched against the
        candidate names per side). Returns ``None`` if no single market matches both teams. The
        orientation step doubles as the both-teams-present check, so a series/futures market
        mentioning only one team can't be picked.
        """
        radiant_aliases = list(radiant_aliases)
        dire_aliases = list(dire_aliases)
        events = await self._discover_events()
        for event_slug, market in self._candidate_game_markets(events):
            outcomes = self._parse_outcomes(market)
            token_ids = self._parse_token_ids(market)
            if len(outcomes) != 2 or len(token_ids) != 2:
                continue
            oriented = self._orient_tokens(outcomes, token_ids, radiant_aliases, dire_aliases)
            if oriented is None:
                continue
            token_radiant, token_dire = oriented
            return ResolvedMarket(
                event_slug=event_slug,
                market_slug=market.get("slug"),
                condition_id=market.get("conditionId") or market.get("condition_id"),
                token_id_radiant=token_radiant,
                token_id_dire=token_dire,
                raw_market=market,
            )
        logger.info(f"No Polymarket game market matched teams {radiant_aliases} vs {dire_aliases}")
        return None

    # ------------------------------------------------------------------ #
    # HTTP
    # ------------------------------------------------------------------ #

    async def _discover_events(self) -> List[Dict[str, Any]]:
        """Fetch active Dota events from Gamma, filtered by tag slug."""
        params: Dict[str, Any] = {"closed": "false", "active": "true", "limit": self.discovery_limit}
        if self.tag_slug:
            params["tag_slug"] = self.tag_slug

        resp = await self.http.get(f"{self.gamma_url}/events", params=params)
        resp.raise_for_status()
        data = resp.json()
        # The events endpoint returns a bare list; tolerate an enveloped form too.
        if isinstance(data, dict):
            return data.get("data") or data.get("events") or []
        return data if isinstance(data, list) else []

    async def _fetch_book(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a token's order book. Returns ``None`` on a 404 'no orderbook' (a resolved/closed
        game's token, or a market that closed between discovery and this call) -- a terminal
        no-market signal, not a transient error. Other HTTP errors propagate."""
        resp = await self.http.get(f"{self.clob_url}/book", params={"token_id": token_id})
        if resp.status_code == 404:
            logger.info(f"No CLOB orderbook for token {token_id[:12]}...; treating as no tradeable market.")
            return None
        resp.raise_for_status()
        book: Dict[str, Any] = resp.json()
        return book

    # ------------------------------------------------------------------ #
    # Parsing helpers (pure; unit-tested directly)
    # ------------------------------------------------------------------ #

    def _candidate_game_markets(self, events: List[Dict[str, Any]]) -> List[Tuple[Optional[str], Dict[str, Any]]]:
        """Flatten events to their target single-game winner markets, carrying the event slug."""
        out: List[Tuple[Optional[str], Dict[str, Any]]] = []
        for event in events:
            event_slug = event.get("slug")
            for market in event.get("markets") or []:
                if self._is_target_game_market(market):
                    out.append((event_slug, market))
        return out

    def _is_target_game_market(self, market: Dict[str, Any]) -> bool:
        """An OPEN single-game winner market for the configured game (Game 1 by default).

        Must still be accepting orders: a resolved/closed game keeps ``active`` and
        ``enableOrderBook`` true but has ``closed=True`` / ``acceptingOrders=False`` and its token
        404s on the CLOB, so those are the reliable open-market discriminators.
        """
        market_type = (market.get("sportsMarketType") or "").strip().lower()
        if market_type != GAME_WINNER_MARKET_TYPE:
            return False
        if market.get("closed") or not market.get("acceptingOrders"):
            return False
        if not self.game_group_title:
            return True
        return self.game_group_title in self._norm(market.get("groupItemTitle"))

    @staticmethod
    def _best(book: Dict[str, Any]) -> Tuple[float, float, float]:
        """Best bid/ask + liquidity from an order book.

        Defensive: compute best by value rather than trusting list order. An empty side falls back
        to the worst possible price (bid 0.0 / ask 1.0) so a one-sided book reads as untradeable
        rather than crashing.
        """
        bids = [float(b["price"]) for b in book.get("bids", []) if "price" in b]
        asks = [float(a["price"]) for a in book.get("asks", []) if "price" in a]
        best_bid = max(bids) if bids else 0.0
        best_ask = min(asks) if asks else 1.0
        liquidity = book.get("liquidity")
        if liquidity is None:
            liquidity = sum(float(b.get("size", 0.0)) for b in book.get("bids", []))
        return best_bid, best_ask, float(liquidity)

    @staticmethod
    def _parse_token_ids(market: Dict[str, Any]) -> List[str]:
        """clobTokenIds arrives as a JSON-encoded string on Gamma; tolerate a real list too."""
        raw = market.get("clobTokenIds") or market.get("clob_token_ids")
        if raw is None:
            return []
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return []
        return [str(t) for t in raw] if isinstance(raw, list) else []

    @staticmethod
    def _parse_outcomes(market: Dict[str, Any]) -> List[str]:
        raw = market.get("outcomes")
        if raw is None:
            return []
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return []
        return [str(o) for o in raw] if isinstance(raw, list) else []

    @staticmethod
    def _norm(text: Optional[str]) -> str:
        return (text or "").strip().lower().replace("-", " ").replace("_", " ")

    def _orient_tokens(
        self,
        outcomes: List[str],
        token_ids: List[str],
        radiant_aliases: Iterable[str],
        dire_aliases: Iterable[str],
    ) -> Optional[Tuple[str, str]]:
        """Map the two outcome tokens to (radiant_token, dire_token) by matching the outcome team
        name (Polymarket's display name) against either side's candidate names. Returns ``None``
        unless both teams match distinct outcomes."""
        r_keys = {self._norm(a) for a in radiant_aliases} - {""}
        d_keys = {self._norm(a) for a in dire_aliases} - {""}
        idx_radiant: Optional[int] = None
        idx_dire: Optional[int] = None
        for i, outcome in enumerate(outcomes):
            norm = self._norm(outcome)
            if any(k in norm or norm in k for k in r_keys):
                idx_radiant = i
            elif any(k in norm or norm in k for k in d_keys):
                idx_dire = i
        if idx_radiant is None or idx_dire is None or idx_radiant == idx_dire:
            return None
        return token_ids[idx_radiant], token_ids[idx_dire]
