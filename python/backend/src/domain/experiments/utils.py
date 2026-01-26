from dataclasses import dataclass
import re
from typing import Optional

from domain.experiments.error import ExperimentNameParseError


@dataclass
class ExperimentParseResult:
    num: str
    parent: str
    change: str


DEFAULT_EXPERIMENT_NAME_PATTERN = "{num}_from_{parent}_{change}"


def parse_experiment_name(
    name: str, pattern: str, raise_error: bool = True
) -> ExperimentParseResult:
    # Convert the pattern like "{num}_from_{parent}_{change}" to regex with named groups
    # Find all field names in the curly braces
    fields = re.findall(r"\{([^{}]+)\}", pattern)
    # Escape the pattern except {fields}, and replace {field} with named groups
    regex_pattern = ""
    last_pos = 0
    for m in re.finditer(r"\{([^{}]+)\}", pattern):
        start, end = m.span()
        # Escape everything between last_pos and start
        regex_pattern += re.escape(pattern[last_pos:start])
        field = m.group(1)
        # For middle fields, be greedy except the last so as to parse correctly
        if field == fields[-1]:
            regex_pattern += f"(?P<{field}>.+)"
        else:
            regex_pattern += f"(?P<{field}>.+?)"
        last_pos = end
    regex_pattern += re.escape(pattern[last_pos:])
    match = re.fullmatch(regex_pattern, name)
    if not match:
        # TODO remove this when add several patterns support to select which one to use
        if raise_error:
            raise ExperimentNameParseError(
                f"Name '{name}' does not match pattern '{pattern}'"
            )
        return ExperimentParseResult(num="", parent="", change=name)
    d = match.groupdict()
    return ExperimentParseResult(
        num=d.get("num", ""), parent=d.get("parent", ""), change=d.get("change", "")
    )
