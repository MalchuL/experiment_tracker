from pydantic import BaseModel, Field


class Rights(BaseModel):
    name: str
    # Can the team member create a new project?
    can_create_project: bool
    # Can the team member do operations on the projects?
    can_edit_project: bool
    can_delete_project: bool
    can_view_project: bool
    # Can the team member manage the project?
    can_create_experiment: bool
    can_edit_experiment: bool
    can_delete_experiment: bool
    can_view_experiment: bool
    # Can the team member manage the hypotheses?
    can_create_hypothesis: bool
    can_edit_hypothesis: bool
    can_delete_hypothesis: bool
    can_view_hypothesis: bool
    # Can the team member manage the team?
    can_edit_team: bool
    can_view_team: bool
    # Other
    description: str = Field(default="")
