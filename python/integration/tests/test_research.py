from uuid import uuid4

import pytest

from conftest import call


def test_project_settings_experiment_lineage_and_pagination(api, project, experiment):
    """Persist project settings and experiment lineage, then paginate and search runs."""
    pid, eid = project["id"], experiment["id"]
    call(
        api,
        "PATCH",
        f"projects/{pid}",
        json={"name": "Renamed project", "description": "Persisted description"},
    )
    assert call(api, "GET", f"projects/{pid}")["name"] == "Renamed project"
    call(
        api,
        "POST",
        f"projects/{pid}/settings",
        json={"name": "epochs", "type": "int", "value": 5},
    )
    call(api, "PATCH", f"projects/{pid}/settings/epochs", json={"value": 10})
    assert call(api, "GET", f"projects/{pid}/settings/map") == {"epochs": 10}
    call(api, "DELETE", f"projects/{pid}/settings/epochs")
    assert call(api, "GET", f"projects/{pid}/settings/map") == {}
    child = call(
        api,
        "POST",
        "experiments",
        json={
            "projectId": pid,
            "name": "Child",
            "parentExperimentId": eid,
            "tags": ["unique-search-tag"],
        },
    )
    call(
        api,
        "PATCH",
        f"experiments/{child['id']}",
        json={
            "status": "running",
            "progress": 42,
            "features": [{"name": "optimizer", "children": [{"name": "adam"}]}],
        },
    )
    read = call(api, "GET", f"experiments/{child['id']}")
    assert (read["parentExperimentId"], read["status"], read["progress"]) == (
        eid,
        "running",
        42,
    )
    assert read["features"][0]["children"][0]["name"] == "adam"
    pages = [
        call(
            api,
            "GET",
            f"projects/{pid}/experiments",
            params={"limit": 1, "offset": offset},
        )
        for offset in (0, 1)
    ]
    assert all(page["total"] == 2 for page in pages)
    assert {page["data"][0]["id"] for page in pages} == {eid, child["id"]}
    filtered = call(
        api,
        "GET",
        f"projects/{pid}/experiments",
        params={"search": "UNIQUE-SEARCH-TAG"},
    )
    assert [row["id"] for row in filtered["data"]] == [child["id"]]


def test_project_team_and_owner_transfers(api, project, make_user):
    """Persist team assignment, team removal, and transfer to another owner."""
    team = call(api, "POST", "teams", json={"name": "Destination"})
    path = f"projects/{project['id']}"
    moved = call(api, "PATCH", path + "/team", json={"teamId": team["id"]})
    assert moved["team"]["id"] == team["id"]
    assert call(api, "GET", path)["team"]["id"] == team["id"]
    standalone = call(api, "PATCH", path + "/team", json={"teamId": None})
    assert standalone["team"] is None
    recipient = make_user()
    moved = call(api, "PATCH", path + "/owner", json={"ownerId": recipient["id"]})
    assert moved["owner"]["id"] == recipient["id"]
    assert call(recipient["client"], "GET", path)["owner"]["id"] == recipient["id"]


def test_hypotheses_reports_and_dashboard(api, project, experiment, make_user):
    """Persist research documents, enforce access, and update dashboard counts."""
    pid = project["id"]
    hypothesis = call(
        api,
        "POST",
        "hypotheses",
        json={
            "projectId": pid,
            "title": "Adam improves loss",
            "author": "Researcher",
            "baseline": experiment["id"],
            "targetMetrics": ["loss"],
        },
    )
    hid = hypothesis["id"]
    call(
        api,
        "PATCH",
        f"hypotheses/{hid}",
        json={"status": "supported", "description": "Measured improvement"},
    )
    read = call(api, "GET", f"hypotheses/{hid}")
    assert read["status"] == "supported" and read["baseline"] == experiment["id"]
    assert call(api, "GET", f"projects/{pid}/hypotheses")["data"][0]["id"] == hid
    call(
        api,
        "PATCH",
        f"experiments/{experiment['id']}",
        json={"status": "complete", "progress": 100},
    )
    stats = call(api, "GET", f"dashboard/project/{pid}/stats")
    assert (
        stats["totalExperiments"],
        stats["completedExperiments"],
        stats["supportedHypotheses"],
    ) == (1, 1, 1)
    report = call(api, "POST", "reports", json={"projectId": pid, "title": "Findings"})
    document = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Adam won"}]}
        ],
    }
    call(
        api,
        "PATCH",
        f"reports/{report['id']}",
        json={"title": "Final findings", "content": document},
    )
    assert call(api, "GET", f"reports/{report['id']}")["content"] == document
    assert (
        call(api, "GET", f"projects/{pid}/reports")["data"][0]["title"]
        == "Final findings"
    )
    outsider = make_user()["client"]
    for path in (f"hypotheses/{hid}", f"reports/{report['id']}"):
        assert outsider.get(path).status_code in (403, 404)
    call(api, "DELETE", f"reports/{report['id']}")
    call(api, "DELETE", f"hypotheses/{hid}")
    call(api, "GET", f"hypotheses/{hid}", status=404)
    assert call(api, "GET", f"dashboard/project/{pid}/stats")["totalHypotheses"] == 0


@pytest.mark.parametrize(
    "path,payload",
    [
        ("projects", {"name": ""}),
        ("teams", {"name": ""}),
        ("experiments", {"projectId": "invalid-uuid", "name": "Run"}),
        ("hypotheses", {"projectId": "invalid-uuid", "title": ""}),
        ("reports", {"projectId": "invalid-uuid", "title": ""}),
        ("users/me/api-tokens", {"name": "Token", "expiresInDays": -1}),
    ],
)
def test_invalid_resource_inputs(api, path, payload):
    """Reject malformed resource creation payloads with validation errors."""
    call(api, "POST", path, status=422, json=payload)


def test_foreign_lineage_is_rejected(api, experiment, make_user):
    """Reject experiment creation in another user's project with a local parent."""
    other = make_user()["client"]
    foreign_project = call(other, "POST", "projects", json={"name": "Foreign"})
    response = api.post(
        "experiments",
        json={
            "projectId": foreign_project["id"],
            "name": "Forbidden",
            "parentExperimentId": experiment["id"],
        },
    )
    assert response.status_code in (403, 404), response.text


def test_missing_experiment_returns_not_found(api):
    """Return 404 when an authenticated user requests a nonexistent experiment."""
    call(api, "GET", f"experiments/{uuid4()}", status=404)
