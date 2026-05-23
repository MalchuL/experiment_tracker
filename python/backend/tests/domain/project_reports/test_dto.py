from uuid import uuid4

import pytest
from pydantic import ValidationError

from domain.project_reports.dto import ProjectReportCreateDTO, ProjectReportUpdateDTO
from experiment_tracker_shared.limits import ENTITY_NAME_MAX_LEN


def test_create_report_title_boundary() -> None:
    ProjectReportCreateDTO(
        project_id=uuid4(),
        title="t" * ENTITY_NAME_MAX_LEN,
    )
    with pytest.raises(ValidationError):
        ProjectReportCreateDTO(
            project_id=uuid4(),
            title="t" * (ENTITY_NAME_MAX_LEN + 1),
        )


def test_update_report_title_boundary() -> None:
    ProjectReportUpdateDTO(title="u" * ENTITY_NAME_MAX_LEN)
    with pytest.raises(ValidationError):
        ProjectReportUpdateDTO(title="u" * (ENTITY_NAME_MAX_LEN + 1))
