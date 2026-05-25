from __future__ import annotations

from dataclasses import dataclass

from experiment_tracker_sdk.utils.experiment_init_strategy.resolving import (
    MultipleItemsResolveStrategy,
)


@dataclass(frozen=True)
class InitParams:
    """Configuration for experiment initialization.

    Args:
        create_project_if_not_exists: Create the project when no match is found.
        create_experiment_if_not_exists: Create the experiment when no match is
            found in the resolved project.
        create_team_if_not_exists: Create the team when no match is found.
        try_existing_project: Reuse an existing matching project before
            creating a new one.
        try_existing_experiment: Reuse an existing matching experiment before
            creating a new one.
        try_existing_team: Reuse an existing matching team before creating a new
            one.
        error_if_name_looks_like_id: When trying existing objects first, raise
            an error if a missing name parses as a UUID instead of creating a
            new object with an ID-like name.
        multiple_items_resolve_strategy: Strategy for resolving ambiguous name
            matches.
    """

    create_project_if_not_exists: bool = False
    create_experiment_if_not_exists: bool = False
    create_team_if_not_exists: bool = False
    try_existing_project: bool = True
    try_existing_experiment: bool = True
    try_existing_team: bool = True
    error_if_name_looks_like_id: bool = True
    multiple_items_resolve_strategy: MultipleItemsResolveStrategy = (
        MultipleItemsResolveStrategy.ERROR
    )
