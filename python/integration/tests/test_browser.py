import os
import re
from uuid import uuid4

import pytest
from playwright.sync_api import expect

from experiment_tracker_sdk import ExpTracker
from experiment_tracker_sdk.client import APIRequestsRegistry, ExperimentTrackerClient

from conftest import call, eventually

pytestmark = pytest.mark.browser


def test_register_login_profile_and_logout(page):
    """Register, reject a bad login, persist profile edits, and enforce logout."""
    email = f"browser-{uuid4().hex}@example.com"
    password = "Browser-password-123!"
    page.goto("/register")
    page.get_by_label("Full Name").fill("Browser Researcher")
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_placeholder("Create a password", exact=True).fill(password)
    page.get_by_placeholder("Confirm your password", exact=True).fill(password)
    page.get_by_role("button", name="Create account", exact=True).click()
    expect(page).to_have_url(re.compile(r"/login$"))
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_placeholder("Enter your password", exact=True).fill(
        "incorrect-password"
    )
    page.get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_text("Login failed", exact=True)).to_be_visible()
    page.get_by_placeholder("Enter your password", exact=True).fill(password)
    page.get_by_role("button", name="Sign in", exact=True).click()
    expect(page).to_have_url(re.compile(r"/projects$"))
    page.goto("/profile")
    page.get_by_label("Display name", exact=True).fill("Edited Browser Researcher")
    page.get_by_role("button", name="Save changes", exact=True).click()
    expect(page.get_by_text("Profile updated", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_label("Display name", exact=True)).to_have_value(
        "Edited Browser Researcher"
    )
    page.get_by_test_id("button-user-menu").click()
    page.get_by_test_id("menu-logout").click()
    expect(page).to_have_url(re.compile(r"/login$"))
    page.goto("/projects")
    expect(page).to_have_url(re.compile(r"/login"))


def test_create_project_and_persist(logged_page, api):
    """Create a project through the UI and verify persistence after reload and via API."""
    page = logged_page
    name = f"Browser project {uuid4().hex[:8]}"
    page.goto("/projects")
    page.get_by_test_id("button-create-project").click()
    page.get_by_label("Name", exact=True).fill(name)
    page.get_by_label("Description", exact=True).fill(
        "Created through the real browser"
    )
    page.get_by_test_id("button-submit-project").click()
    expect(page.get_by_text(name, exact=True).first).to_be_visible()
    page.reload()
    expect(page.get_by_text(name, exact=True).first).to_be_visible()
    projects = call(api, "GET", "projects")["data"]
    assert (
        next(row for row in projects if row["name"] == name)["description"]
        == "Created through the real browser"
    )


def test_profile_password_change_in_browser(logged_page, api, user):
    """Change a password through the UI and accept only the new password at login."""
    page = logged_page
    page.goto("/profile")
    page.get_by_role("button", name=re.compile("Change password")).click()
    page.get_by_label("Current password", exact=True).fill(user["password"])
    page.get_by_label("New password", exact=True).fill("Changed-browser-password-123!")
    page.get_by_label("Confirm new password", exact=True).fill(
        "Changed-browser-password-123!"
    )
    page.get_by_role("button", name="Update password", exact=True).click()
    expect(page.get_by_text("Password updated", exact=True)).to_be_visible()
    call(
        api,
        "POST",
        "auth/jwt/login",
        status=400,
        data={"username": user["email"], "password": user["password"]},
    )
    assert call(
        api,
        "POST",
        "auth/jwt/login",
        data={"username": user["email"], "password": "Changed-browser-password-123!"},
    )["access_token"]


def test_browser_token_creation_persists(logged_page, api):
    """Create a PAT through the UI and verify it remains listed after reload."""
    page = logged_page
    page.goto("/profile/api-tokens")
    page.get_by_role("button", name="Create token", exact=True).click()
    page.get_by_placeholder("Training cluster token").fill("Browser token")
    page.get_by_role("button", name="Create token", exact=True).last.click()
    expect(page.get_by_text("Browser token", exact=True)).to_be_visible()
    tokens = call(api, "GET", "users/me/api-tokens")["data"]
    assert len(tokens) == 1 and tokens[0]["name"] == "Browser token"
    page.reload()
    expect(page.get_by_text("Browser token", exact=True)).to_be_visible()


def test_dashboard_renders_counts(logged_page, api, project, experiment):
    """Display persisted experiment completion counts and percentages after reload."""
    call(api, "PATCH", f"experiments/{experiment['id']}", json={"status": "complete"})
    page = logged_page
    page.goto(f"/projects/{project['id']}")
    expect(page.get_by_text("100%", exact=True)).to_be_visible()
    expect(
        page.get_by_text("Completed", exact=True)
        .locator("..")
        .get_by_text("1", exact=True)
    ).to_be_visible()
    page.reload()
    expect(page.get_by_text("100%", exact=True)).to_be_visible()


def test_create_hypothesis_in_browser(logged_page, api, project):
    """Create a hypothesis through the UI and verify its title and author persist."""
    page = logged_page
    page.goto(f"/projects/{project['id']}/hypotheses")
    page.get_by_test_id("button-create-hypothesis").click()
    page.get_by_test_id("input-hypothesis-title").fill("Browser hypothesis")
    page.get_by_test_id("input-hypothesis-description").fill(
        "A reproducible research hypothesis"
    )
    page.get_by_test_id("input-hypothesis-author").fill("Browser Author")
    page.get_by_test_id("button-submit-hypothesis").click()
    expect(page.get_by_text("Browser hypothesis", exact=True).first).to_be_visible()
    page.reload()
    expect(page.get_by_text("Browser hypothesis", exact=True).first).to_be_visible()
    assert (
        call(api, "GET", f"projects/{project['id']}/hypotheses")["data"][0]["author"]
        == "Browser Author"
    )


def test_report_editor_persists_document(logged_page, api, project):
    """Save a report title and editor content, then verify reload and API readback."""
    report = call(
        api,
        "POST",
        "reports",
        json={"projectId": project["id"], "title": "Browser draft"},
    )
    page = logged_page
    page.goto(f"/projects/{project['id']}/reports/{report['id']}")
    page.get_by_placeholder("Untitled report").fill("Browser findings")
    editor = page.locator("[contenteditable=true]")
    editor.fill("These findings survive reload.")
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_text("Saved", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_placeholder("Untitled report")).to_have_value("Browser findings")
    expect(page.locator("[contenteditable=true]")).to_contain_text(
        "These findings survive reload."
    )
    assert (
        call(api, "GET", f"reports/{report['id']}")["content"]["content"][0]["content"][
            0
        ]["text"]
        == "These findings survive reload."
    )


def test_hypothesis_card_opens_details(logged_page, api, project):
    """Open a hypothesis card and require a working detail page with its title."""
    hypothesis = call(
        api,
        "POST",
        "hypotheses",
        json={
            "projectId": project["id"],
            "title": "Hypothesis detail journey",
            "author": "Browser Author",
        },
    )
    page = logged_page
    page.goto(f"/projects/{project['id']}/hypotheses")
    page.get_by_test_id(f"card-hypothesis-{hypothesis['id']}").click()
    expect(page).to_have_url(re.compile(f"/hypotheses/{hypothesis['id']}$"))
    response = page.request.get(page.url)
    assert response.status == 200, (
        f"Hypothesis card navigated to {page.url}, which returned {response.status}"
    )
    expect(page.get_by_text("Hypothesis detail journey", exact=True)).to_be_visible()


def test_named_artifact_browser_preview_and_download(
    logged_page, tracker, project, experiment
):
    """Preview a named artifact after reload and download its original bytes."""
    payload = "Preview rendered through Next.js\n"
    tracker.log_final_artifact(
        "browser-output",
        payload,
        stored_filepath="output.txt",
        default_content_type="text/plain",
    )
    page = logged_page
    page.goto(f"/projects/{project['id']}/experiments/{experiment['id']}/artifacts")
    page.get_by_test_id("tab-details-artifacts").click()
    page.get_by_role("button", name="Expand artifact preview").click()
    expect(page.get_by_text(payload.strip(), exact=True)).to_be_visible()
    with page.expect_download() as download:
        page.get_by_role("link", name="Download", exact=True).click()
    assert download.value.failure() is None
    from pathlib import Path

    assert Path(download.value.path()).read_bytes() == payload.encode()
    page.reload()
    page.get_by_test_id("tab-details-artifacts").click()
    page.get_by_role("button", name="Expand artifact preview").click()
    expect(page.get_by_text(payload.strip(), exact=True)).to_be_visible()


def test_step_artifact_browser_proxy(logged_page, tracker, experiment):
    """Fetch step artifact bytes through the BFF with MIME type and no-store headers."""
    from experiment_tracker_sdk.client import ArtifactClient

    client = ArtifactClient(tracker._api_requests_registry, tracker._request_client)
    eid = experiment["id"]
    client.upload_and_log_experiment_artifact_at_step(
        eid, "output.txt", b"step browser output", "text/plain", "output", "text", 3
    )
    page = logged_page
    page.goto("/projects")
    response = page.evaluate(
        """async url => {
        const response = await fetch(url);
        return {status: response.status, text: await response.text(), contentType: response.headers.get('content-type'), cache: response.headers.get('cache-control')};
    }""",
        f"/api/experiment-artifacts/{eid}/download-at-step?step=3&name=output",
    )
    assert response["status"] == 200 and response["text"] == "step browser output", (
        response
    )
    assert (
        response["contentType"].startswith("text/plain")
        and response["cache"] == "no-store"
    )


def test_kanban_drag_persists_status(logged_page, api, project, experiment):
    """Drag an experiment to Running and verify its status through API and reload."""
    page = logged_page
    page.goto(f"/projects/{project['id']}/kanban")
    card = page.get_by_test_id(f"kanban-card-{experiment['id']}")
    target = page.get_by_test_id("kanban-drop-running")
    expect(card).to_be_visible()
    expect(target).to_be_visible()
    source_box, target_box = card.bounding_box(), target.bounding_box()
    page.mouse.move(
        source_box["x"] + source_box["width"] / 2,
        source_box["y"] + source_box["height"] / 2,
    )
    page.mouse.down()
    page.mouse.move(
        target_box["x"] + target_box["width"] / 2,
        target_box["y"] + target_box["height"] / 2,
        steps=20,
    )
    page.mouse.up()
    eventually(
        lambda: call(api, "GET", f"experiments/{experiment['id']}"),
        lambda row: row["status"] == "running",
    )
    page.reload()
    expect(
        page.get_by_test_id("kanban-column-running").get_by_test_id(
            f"kanban-card-{experiment['id']}"
        )
    ).to_be_visible()


def test_dag_renders_persisted_parent_relationship(
    logged_page, api, project, experiment
):
    """Render parent and child experiment nodes with their edge after reload."""
    child = call(
        api,
        "POST",
        "experiments",
        json={
            "projectId": project["id"],
            "name": "DAG child",
            "parentExperimentId": experiment["id"],
        },
    )
    page = logged_page
    page.goto(f"/projects/{project['id']}/dag")
    expect(page.get_by_test_id(f"dag-node-{experiment['id']}")).to_be_visible()
    expect(page.get_by_test_id(f"dag-node-{child['id']}")).to_be_visible()
    expect(page.locator(".react-flow__edge")).to_have_count(1)
    page.reload()
    expect(page.locator(".react-flow__edge")).to_have_count(1)


@pytest.fixture
def comparison(api, project, user, tmp_path):
    """Seed two runs with distinct hparams, metrics, scalars, and snapshot contents."""
    experiments = []
    for name, value in (("Compare baseline", 2), ("Compare improved", 7)):
        experiment = call(
            api,
            "POST",
            "experiments",
            json={
                "projectId": project["id"],
                "name": name,
                "color": "#ff0000" if value == 2 else "#0000ff",
            },
        )
        eid = experiment["id"]
        call(
            api,
            "PUT",
            f"experiments/{eid}/hparams",
            json={"hparams": {"epochs": value, "variant": name}},
        )
        call(
            api,
            "POST",
            "metrics",
            json={"experimentId": eid, "name": "score", "value": value},
        )
        call(
            api,
            "POST",
            f"scalars/log_batch/{eid}",
            json={
                "scalars": [
                    {"step": step, "scalars": {"loss": float(value + step)}}
                    for step in range(3)
                ]
            },
        )
        source = tmp_path / str(value)
        source.mkdir()
        (source / "train.py").write_text(f"epochs = {value}\n")
        client = ExperimentTrackerClient(
            os.environ["INTEGRATION_API_URL"].removesuffix("/api"), user["token"]
        )
        tracker = ExpTracker(eid, project["id"], APIRequestsRegistry(), client)
        try:
            tracker.log_snapshot(source, root=source)
        finally:
            tracker.close()
        experiments.append(experiment)
    return experiments


@pytest.mark.parametrize("tab", ["HParams", "Metrics", "Scalars", "Files"])
def test_browser_comparison_data(logged_page, project, comparison, tab):
    """Display both runs' persisted values or file contents in each comparison tab."""
    page = logged_page
    ids = "&".join(f"exp={row['id']}" for row in comparison)
    page.goto(f"/projects/{project['id']}/compare?{ids}")
    page.get_by_role("tab", name=tab, exact=True).click()
    panel = page.get_by_role("tabpanel")
    if tab == "HParams":
        expect(panel.get_by_text("epochs", exact=True)).to_be_visible()
        expect(panel.get_by_text("2", exact=True).first).to_be_visible()
        expect(panel.get_by_text("7", exact=True).first).to_be_visible()
    elif tab == "Metrics":
        expect(panel.get_by_text("score", exact=True).first).to_be_visible()
        expect(panel.get_by_text("2", exact=True).first).to_be_visible()
        expect(panel.get_by_text("7", exact=True).first).to_be_visible()
    elif tab == "Scalars":
        panel.get_by_role("button", name="Add plot", exact=True).click()
        panel.get_by_placeholder("Search scalars...").fill("loss")
        page.get_by_role("option", name="loss", exact=True).click()
        page.wait_for_function(
            "() => [...document.querySelectorAll('.js-plotly-plot')].some(p => p.data?.filter(s => s.y?.length).length >= 2)"
        )
        series = page.locator(".js-plotly-plot").first.evaluate(
            "p => p.data.filter(s => s.y?.length).map(s => Array.from(s.y))"
        )
        assert [2, 3, 4] in series and [7, 8, 9] in series, series
    else:
        panel.get_by_text("train.py", exact=True).first.click()
        expect(panel.get_by_text("epochs = 2", exact=True).first).to_be_visible()
        expect(panel.get_by_text("epochs = 7", exact=True).first).to_be_visible()


def test_team_creation_browser(logged_page, api):
    """Create a team through the UI and verify reload and API persistence."""
    page = logged_page
    name = f"Browser team {uuid4().hex[:8]}"
    page.goto("/teams")
    page.get_by_test_id("button-teams-new-team").click()
    page.get_by_test_id("input-create-team-name").fill(name)
    page.get_by_test_id("button-submit-create-team").click()
    expect(page.get_by_text(name, exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_text(name, exact=True)).to_be_visible()
    assert any(row["name"] == name for row in call(api, "GET", "teams")["data"])


def test_admin_browser_unlock_search_and_storage(page, user):
    """Reject a bad admin key, retain a valid unlock, and expose storage search."""
    page.goto("/admin")
    page.get_by_placeholder("Admin key").fill("incorrect-key")
    page.get_by_role("button", name="Unlock", exact=True).click()
    expect(page.get_by_role("alert")).to_be_visible()
    page.get_by_placeholder("Admin key").fill(os.environ["INTEGRATION_ADMIN_KEY"])
    page.get_by_role("button", name="Unlock", exact=True).click()
    page.get_by_placeholder("Search by email, name, or UUID…").fill(user["email"])
    expect(page.locator(f'input[value="{user["email"]}"]')).to_be_visible()
    page.reload()
    expect(page.get_by_role("heading", name="Admin", exact=True)).to_be_visible()
    page.goto("/admin/storage")
    expect(page.get_by_placeholder("Search bucket name…")).to_be_visible()
    expect(
        page.get_by_placeholder("Search table name (e.g. project uuid fragment)…")
    ).to_be_visible()


def test_browser_denies_foreign_project(logged_page, make_user):
    """Deny another user's project without exposing its name or losing the session UI."""
    other = make_user()["client"]
    project = call(other, "POST", "projects", json={"name": "Private browser project"})
    page = logged_page
    with page.expect_response(
        lambda response: response.url.endswith(f"/api/projects/{project['id']}")
    ) as denied:
        page.goto(f"/projects/{project['id']}/experiments")
    assert denied.value.status in (403, 404)
    expect(page.get_by_text("Private browser project", exact=True)).to_have_count(0)
    expect(page.get_by_test_id("button-user-menu")).to_be_visible()
