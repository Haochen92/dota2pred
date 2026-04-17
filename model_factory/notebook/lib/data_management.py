"""
Reusable data fetching and loading helpers for the feature engineering notebooks.

This module centralizes the logic to:
- Look up patch windows
- Fetch pro matches (with outcomes) in those windows
- Materialize a modeling-friendly DataFrame and optionally persist it to Parquet
- Load the DataFrame back from disk

All DB access is asynchronous — call these helpers with `await` in notebooks.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import pandas as pd

from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.repositories.patch_repository import PatchRepository
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.models.match.table import MatchTable
from dota_oracle_common.models.patches.table import PatchTable

import json
from datetime import datetime
from typing import Dict, Any

from dota_oracle_common.models.match.table import MatchOutcomeTable


# Default patch set for quick experiments (override in calls if needed)
PATCHES_LIST: Sequence[str] = ("7.37", "7.38", "7.39")


async def fetch_pro_matches(
    *,
    patch_numbers: Iterable[str] = PATCHES_LIST,
    relationship_fields: Sequence[str] = ("outcome",),
) -> Tuple[List[MatchTable], pd.DataFrame]:
    """
    Fetch pro matches for the given patch windows and return:
    - the raw MatchTable objects (for feature generators)
    - a tidy DataFrame with {match_id, patch, radiant_win, start_time}

    Notes
    - Results are computed causally: we sort by start_time ascending.
    - Only matches with an outcome are included (label required for modeling).
    - `relationship_fields` defaults to ["outcome"] to eager-load outcomes.
    """
    session_factory = DatabaseManager.get_session_factory()

    # Step 1: Resolve patch windows
    async with session_factory() as session:
        patch_repo = PatchRepository(session)
        patches: List[PatchTable] = []
        for p in patch_numbers:
            patch = await patch_repo.get_patch_by_number(p)
            if patch is not None:
                patches.append(patch)

    if not patches:
        # No patches found — return empty structures
        return [], pd.DataFrame(columns=["match_id", "patch", "radiant_win", "start_time"])  # type: ignore[return-value]

    # Step 2: Fetch matches within each patch window
    all_match_tables: List[MatchTable] = []
    all_match_records: List[dict] = []

    async with session_factory() as session:
        match_repo = MatchRepository(session)

        for patch in patches:
            matches = await match_repo.get_match_details(
                relationship_fields=list(relationship_fields),
                start_time=patch.start_time,  # use datetimes to match column type
                end_time=patch.end_time,
            )

            for match in matches:
                if not match.outcome:
                    # Skip unlabeled rows; they don't help modeling and cannot update state
                    continue
                all_match_tables.append(match)
                all_match_records.append(
                    {
                        "match_id": match.match_id,
                        "patch": patch.patch_number,
                        "radiant_win": match.outcome.radiant_win,
                        "start_time": match.start_time,
                    }
                )

    # Step 3: Ensure chronological ordering (causal correctness)
    all_match_tables.sort(key=lambda m: m.start_time)
    all_match_records.sort(key=lambda r: r["start_time"])  # type: ignore[index]

    df = pd.DataFrame(all_match_records)
    return all_match_tables, df


def save_pro_matches_parquet(df: pd.DataFrame, *, path: str) -> str:
    """Save the provided DataFrame to a Parquet file and return the path."""
    if not path.lower().endswith(".parquet"):
        raise ValueError("path must be a .parquet file path")
    df.to_parquet(path, index=False)
    return path


def load_pro_matches_parquet(path: str) -> pd.DataFrame:
    """
    Load the modeling DataFrame from a Parquet file.

    Returns a DataFrame with columns: match_id, patch, radiant_win, start_time
    (schema matches what `fetch_pro_matches` produces and `save_pro_matches_parquet` persists).
    """
    return pd.read_parquet(path)


def load_data(*, data_dir: str = "../data/", file_name: str = "pro_match_dataset_.parquet") -> pd.DataFrame:
    """Convenience loader that assembles a path and loads the Parquet file."""
    path = f"{data_dir.rstrip('/')}/{file_name}"
    return load_pro_matches_parquet(path)


# ---------------------------------------------------------------------------
# Persistence helpers for full MatchTable objects
# ---------------------------------------------------------------------------


def _match_to_dict(m: MatchTable) -> Dict[str, Any]:
    base = m.model_dump()
    # Normalize datetime to ISO8601 for JSON
    st = base.get("start_time")
    if isinstance(st, datetime):
        base["start_time"] = st.isoformat()
    # Relationship: outcome (optional)
    if getattr(m, "outcome", None) is not None:
        base["outcome"] = m.outcome.model_dump()  # type: ignore[attr-defined]
    return base


def _dict_to_match(d: Dict[str, Any]) -> MatchTable:
    data = dict(d)
    outcome_payload = data.pop("outcome", None)
    # Parse datetime
    st = data.get("start_time")
    if isinstance(st, str):
        try:
            data["start_time"] = datetime.fromisoformat(st)
        except ValueError:
            pass
    match = MatchTable.model_validate(data)
    if outcome_payload is not None:
        try:
            match.outcome = MatchOutcomeTable.model_validate(outcome_payload)
        except Exception:
            match.outcome = MatchOutcomeTable(**outcome_payload)
    return match


def save_match_tables_jsonl(matches: List[MatchTable], *, path: str) -> str:
    """
    Persist a list of MatchTable objects (including outcome, if present) to JSONL.

    - Datetimes are stored as ISO8601 strings.
    - One JSON object per line for streaming-friendly access.
    """
    with open(path, "w", encoding="utf-8") as f:
        for m in matches:
            rec = _match_to_dict(m)
            f.write(json.dumps(rec, ensure_ascii=False))
            f.write("\n")
    return path


def load_match_tables_jsonl(path: str) -> List[MatchTable]:
    """Load MatchTable objects (with outcomes when present) from a JSONL file."""
    out: List[MatchTable] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out.append(_dict_to_match(obj))
    out.sort(key=lambda m: m.start_time)
    return out


__all__ = [
    "PATCHES_LIST",
    "fetch_pro_matches",
    "save_pro_matches_parquet",
    "load_pro_matches_parquet",
    "save_match_tables_jsonl",
    "load_match_tables_jsonl",
]
