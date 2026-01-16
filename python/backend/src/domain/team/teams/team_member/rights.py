from pydantic import BaseModel, Field


class Rights(BaseModel):
    name: str
    # Can the team member create a new project?
    can_create_projects: bool
    # Can the team member do operations on the projects?
    can_delete_projects: bool
    can_view_projects: bool
    # Can the team member manage the team?
    can_edit_team: bool
    can_view_team: bool
    # Other
    description: str = Field(default="")
