from typing import List


DEFAULT_EXPERIMENT_NAME_PATTERN = "{num}_from_{parent}_{change}"
DEFAULT_METRICS: List[str] = []


def default_metrics():
    return {
        "namingPattern": DEFAULT_EXPERIMENT_NAME_PATTERN,
        "displayMetrics": DEFAULT_METRICS,
    }
