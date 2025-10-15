from typing import Optional
import optuna
from optuna.trial import TrialState
import pandas as pd

def load_study(storage_url: str, study_name: Optional[str] = None) -> optuna.Study:
    """Load a study by name from the Optuna storage."""
    return optuna.load_study(study_name=study_name, storage=storage_url)

def trials_df(study: optuna.Study):
    """Get all trials as a tidy DataFrame (only completed by default)."""
    import pandas as pd
    trials = study.get_trials(deepcopy=False, states=(TrialState.COMPLETE,))
    rows = []
    for t in trials:
        row = {"number": t.number, "value": t.value, "state": t.state.name, "duration": (t.datetime_complete - t.datetime_start).total_seconds() if t.datetime_complete else None}
        row.update({f"param_{k}": v for k, v in t.params.items()})
        row.update({f"userattr_{k}": v for k, v in t.user_attrs.items()})
        rows.append(row)
    return pd.DataFrame(rows).sort_values("value", ascending=(study.direction.name == "MINIMIZE"))

def best_params_and_value(study: optuna.Study):
    return study.best_params, study.best_value




