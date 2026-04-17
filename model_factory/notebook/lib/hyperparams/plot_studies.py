import optuna
import pandas as pd
from typing import Tuple, Iterable, List
from optuna.trial import TrialState
from optuna.visualization import (
    plot_optimization_history,
    plot_param_importances,
    plot_slice,
    plot_parallel_coordinate,
    plot_contour,
    plot_edf,
)
from IPython.display import display


def importance_table(study: optuna.study.Study, top_k: int = 10) -> pd.DataFrame:
    """Tabular param importances (sorted)."""
    from optuna.importance import get_param_importances

    imps = get_param_importances(study)  # FANOVA by default if available
    df = (
        pd.DataFrame(list(imps.items()), columns=["param", "importance"])
        .sort_values("importance", ascending=False)
        .head(top_k)
        .reset_index(drop=True)
    )
    return df


def top_params(study: optuna.study.Study, k: int = 6) -> List[str]:
    """Pick top-k params by importance."""
    return importance_table(study, top_k=k)["param"].tolist()


def valid_pairs(study: optuna.study.Study, params: Iterable[str], min_trials: int = 10) -> List[Tuple[str, str]]:
    """Param pairs that co-occur in >= min_trials."""
    from collections import defaultdict
    from itertools import combinations

    counts = defaultdict(int)
    for t in study.get_trials(deepcopy=False, states=(TrialState.COMPLETE,)):
        keys = [p for p in t.params.keys() if p in params]
        for a, b in combinations(sorted(keys), 2):
            counts[(a, b)] += 1
    return [pair for pair, c in counts.items() if c >= min_trials]


def plot_study(
    study: optuna.study.Study,
    *,
    k_params: int = 6,
    min_pairs: int = 10,
    show_parallel: bool = False,
    show_contour: bool = False,
    show_edf: bool = False,
) -> None:
    """Minimal, high-signal plots with guardrails to avoid clutter."""
    # 1) Always
    plot_optimization_history(study).show()

    # 2) Importances (bar) + table print
    plot_param_importances(study).show()
    try:
        df_imp = importance_table(study, top_k=k_params)
        display(df_imp)  # in Jupyter; or print(df_imp.to_string(index=False))
    except Exception as e:
        print("importance_table error:", e)

    # 3) Slice for top params
    params = top_params(study, k=k_params)
    if params:
        plot_slice(study, params=params).show()

    # 4) Parallel coordinate (optional, top params)
    if show_parallel and params:
        plot_parallel_coordinate(study, params=params).show()

    # 5) Contour only for co-occurring pairs (optional)
    if show_contour and params:
        for a, b in valid_pairs(study, params, min_trials=min_pairs):
            plot_contour(study, params=[a, b]).show()

    # 6) EDF (optional; best for comparing multiple studies)
    if show_edf:
        plot_edf(study).show()

    # 7) Top trials DataFrame
    df_top_trials = get_top_trials_df(study)
    display(df_top_trials)


def get_top_trials_df(study: optuna.Study, n_trials: int = 10) -> pd.DataFrame:
    """
    Extracts the top performing trials from an Optuna study into a pandas DataFrame.

    The function sorts trials based on their objective value, respecting the
    study's optimization direction (minimization or maximization).

    Args:
        study: The Optuna study object to analyze.
        n_trials: The number of top trials to return.

    Returns:
        A pandas DataFrame containing the top trials, with columns for rank,
        objective value, trial number, and all hyperparameters. Returns an
        empty DataFrame if the study has no completed trials.
    """
    # 1. Get only the trials that completed successfully
    completed_trials = [t for t in study.trials if t.state == TrialState.COMPLETE and t.value is not None]

    # Handle the case with no completed trials
    if not completed_trials:
        return pd.DataFrame()

    # 2. Sort them based on the study's optimization direction
    is_maximize = study.direction == optuna.study.StudyDirection.MAXIMIZE
    sorted_trials = sorted(completed_trials, key=lambda t: t.value, reverse=is_maximize)

    # 3. Select the top N trials and prepare data for the DataFrame
    top_trials = sorted_trials[:n_trials]

    trial_data = []
    for i, trial in enumerate(top_trials):
        # Start with the core trial information
        row = {"rank": i + 1, "value": trial.value, "trial_num": trial.number}
        # Add all hyperparameters from the trial to the same dictionary
        row.update(trial.params)
        trial_data.append(row)

    # 4. Create and return the DataFrame
    return pd.DataFrame(trial_data)
