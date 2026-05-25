from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .client import ExperimentClient

DEFAULT_EXPERIMENT_NAME_PATTERN = "{num}_from_{parent}_{change}"


@dataclass
class ExperimentNameParseResult:
    num: str
    parent: str
    change: str


def parse_experiment_name(
    name: str, pattern: str = DEFAULT_EXPERIMENT_NAME_PATTERN
) -> ExperimentNameParseResult:
    fields = re.findall(r"\{([^{}]+)\}", pattern)
    regex_pattern = ""
    last_pos = 0

    for match in re.finditer(r"\{([^{}]+)\}", pattern):
        start, end = match.span()
        regex_pattern += re.escape(pattern[last_pos:start])
        field = match.group(1)
        if field == fields[-1]:
            regex_pattern += f"(?P<{field}>.+)"
        else:
            regex_pattern += f"(?P<{field}>.+?)"
        last_pos = end

    regex_pattern += re.escape(pattern[last_pos:])
    parsed = re.fullmatch(regex_pattern, name)
    if not parsed:
        raise ValueError(f"Name '{name}' does not match pattern '{pattern}'")

    groups = parsed.groupdict()
    return ExperimentNameParseResult(
        num=groups.get("num", ""),
        parent=groups.get("parent", ""),
        change=groups.get("change", ""),
    )


def get_parent_experiment_id_by_name(
    client: ExperimentClient,
    project_id: str,
    *,
    experiment_name: Optional[str] = None,
    parent_name: Optional[str] = None,
    pattern: str = DEFAULT_EXPERIMENT_NAME_PATTERN,
) -> Optional[str]:
    """Resolve a parent experiment id by parsing names and fetching project experiments."""
    if experiment_name:
        parent_num = parse_experiment_name(experiment_name, pattern).parent
    elif parent_name:
        parent_num = parse_experiment_name(parent_name, pattern).num
    else:
        return None

    if not parent_num:
        return None

    experiments = client.get_project_experiments(project_id)
    for experiment in experiments:
        parsed = parse_experiment_name(experiment.name, pattern)
        if parsed.num == parent_num:
            return experiment.id

    return None
