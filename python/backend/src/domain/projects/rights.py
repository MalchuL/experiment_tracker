from dataclasses import dataclass


@dataclass
class ProjectRights:
    can_edit_project: bool
    can_delete_project: bool
    can_view_project: bool

    can_create_experiment: bool
    can_edit_experiment: bool
    can_delete_experiment: bool
    can_view_experiment: bool

    can_create_hypothesis: bool
    can_edit_hypothesis: bool
    can_delete_hypothesis: bool
    can_view_hypothesis: bool

    can_create_metric: bool
    can_edit_metric: bool
    can_delete_metric: bool
    can_view_metric: bool
