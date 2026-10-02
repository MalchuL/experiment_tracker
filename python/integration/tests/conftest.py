"""Real HTTP fixtures, deliberately outside the services' mocking conftests."""

import json
import os
from pathlib import Path
import time
from uuid import uuid4

import httpx
import pytest

from experiment_tracker_sdk import ExpTracker
from experiment_tracker_sdk.client import APIRequestsRegistry, ExperimentTrackerClient
from experiment_tracker_sdk.client.api_access import ExpTrackerApiAccess
from experiment_tracker_sdk.settings import get_exp_tracker_settings

reports = []


def call(client, method, path, *, status=200, **kwargs):
    """Assert the expected HTTP status and return JSON, or None for an empty body."""
    response = client.request(method, path, **kwargs)
    assert response.status_code == status, (
        f"{method} {path}: expected {status}, got {response.status_code}: {response.text[:2000]}"
    )
    return response.json() if response.content else None


def eventually(fetch, predicate, timeout=15):
    """Poll readback every 250 ms until the predicate succeeds or the timeout fails."""
    deadline = time.monotonic() + timeout
    while True:
        result = fetch()
        if predicate(result):
            return result
        assert time.monotonic() < deadline, (
            f"Readback did not converge within {timeout}s: {result}"
        )
        time.sleep(0.25)


@pytest.fixture
def make_user():
    """Provide a unique authenticated user factory and close all clients on teardown."""
    clients = []

    def create():
        """Register and log in a fresh user, returning credentials and an HTTP client."""
        client = httpx.Client(
            base_url=os.environ["INTEGRATION_API_URL"] + "/",
            timeout=30,
            trust_env=False,
        )
        clients.append(client)
        email = f"integration-{uuid4().hex}@example.com"
        password = "Integration-password-123!"
        user = call(
            client,
            "POST",
            "auth/register",
            status=201,
            json={"email": email, "password": password},
        )
        login = call(
            client,
            "POST",
            "auth/jwt/login",
            data={"username": email, "password": password},
        )
        client.headers["Authorization"] = f"Bearer {login['access_token']}"
        return {
            "client": client,
            "email": email,
            "password": password,
            "id": user["id"],
            "token": login["access_token"],
        }

    yield create
    for client in clients:
        client.close()


@pytest.fixture
def user(make_user):
    """Create an isolated authenticated user for the test."""
    return make_user()


@pytest.fixture
def api(user):
    """Provide the test user's authenticated backend HTTP client."""
    return user["client"]


@pytest.fixture
def project(api):
    """Create a uniquely named project owned by the test user."""
    return call(api, "POST", "projects", json={"name": f"Project-{uuid4().hex[:8]}"})


@pytest.fixture
def experiment(api, project):
    """Create a baseline experiment in the test user's project."""
    return call(
        api,
        "POST",
        "experiments",
        json={"projectId": project["id"], "name": "Baseline"},
    )


@pytest.fixture
def tracker(user, project, experiment):
    """Provide an SDK tracker for the baseline experiment and close it on teardown."""
    client = ExperimentTrackerClient(
        os.environ["INTEGRATION_API_URL"].removesuffix("/api"), user["token"]
    )
    result = ExpTracker(experiment["id"], project["id"], APIRequestsRegistry(), client)
    yield result
    result.close()


@pytest.fixture
def sdk_config(api, tmp_path, monkeypatch):
    """Isolate SDK and CLI configuration with a PAT, restoring singleton state afterward."""
    # Isolate both on-disk CLI configuration and the SDK's process-wide singleton.
    scopes = [
        "project.view",
        "project.edit",
        "project.delete",
        "projects.create",
        "experiments.create",
        "experiments.view",
        "experiments.edit",
        "experiments.delete",
        "metrics.create",
        "metrics.view",
        "metrics.edit",
        "scalars.log",
        "scalars.view",
        "artifacts.log",
        "artifacts.view",
        "teams.view",
        "teams.create",
    ]
    token = call(
        api,
        "POST",
        "users/me/api-tokens",
        json={"name": "Integration SDK", "scopes": scopes},
    )
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "base_url": os.environ["INTEGRATION_API_URL"].removesuffix("/api"),
                "api_token": token["token"],
                "api_prefix": "/api",
            }
        )
    )
    for name in (
        "EXP_TRACKER_API_TOKEN",
        "EXP_TRACKER_BASE_URL",
        "EXP_TRACKER_API_PREFIX",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("EXP_TRACKER_CONFIG_PATH", str(config))
    get_exp_tracker_settings.cache_clear()
    previous = ExpTrackerApiAccess._instance
    ExpTrackerApiAccess._instance = None
    yield config
    if ExpTrackerApiAccess._instance is not None:
        ExpTrackerApiAccess._instance.request_client.close()
    ExpTrackerApiAccess._instance = previous
    get_exp_tracker_settings.cache_clear()


@pytest.fixture
def admin():
    """Provide a backend client authenticated with the integration admin key."""
    with httpx.Client(
        base_url=os.environ["INTEGRATION_API_URL"] + "/",
        headers={"X-Admin-Key": os.environ["INTEGRATION_ADMIN_KEY"]},
        timeout=30,
        trust_env=False,
    ) as client:
        yield client


@pytest.fixture
def browser_context_args(browser_context_args):
    """Configure the browser's integration web origin and viewport."""
    return {
        **browser_context_args,
        "base_url": os.environ["INTEGRATION_WEB_URL"],
        "viewport": {"width": 1440, "height": 1000},
    }


@pytest.fixture
def logged_page(page, user):
    """Authenticate the browser page by setting the test user's session cookie."""
    page.context.add_cookies(
        [
            {
                "name": "auth_token",
                "value": user["token"],
                "url": os.environ["INTEGRATION_WEB_URL"],
            }
        ]
    )
    return page


@pytest.fixture(autouse=True)
def browser_diagnostics(request):
    """Capture browser exceptions, console errors, and failing HTTP responses to a log."""
    if request.node.get_closest_marker("browser") is None:
        yield
        return
    page = request.getfixturevalue("page")
    page.set_default_timeout(15000)
    events = []
    page.on("pageerror", lambda error: events.append(f"pageerror: {error}"))
    page.on(
        "console",
        lambda message: (
            events.append(f"console {message.type}: {message.text}")
            if message.type == "error"
            else None
        ),
    )
    page.on(
        "response",
        lambda response: (
            events.append(f"HTTP {response.status}: {response.url}")
            if response.status >= 400
            else None
        ),
    )
    yield
    if events:
        directory = Path(os.environ["INTEGRATION_RESULTS_DIR"])
        filename = request.node.nodeid.replace("/", "_").replace(":", "_")
        (directory / f"{filename}.browser.log").write_text("\n".join(events))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Append failed pytest phases and reproduction commands to the results directory."""
    outcome = yield
    report = outcome.get_result()
    if report.failed and os.environ.get("INTEGRATION_RESULTS_DIR"):
        with (Path(os.environ["INTEGRATION_RESULTS_DIR"]) / "failures.txt").open(
            "a"
        ) as output:
            output.write(
                f"\n{item.nodeid} ({report.when})\nReproduce: ./scripts/test-integration.sh {item.nodeid}\n{report.longrepr}\n"
            )


def pytest_runtest_logreport(report):
    """Collect test outcomes and setup failures for the session summary."""
    if report.when == "call" or (report.failed and report.when == "setup"):
        reports.append(
            {"test": report.nodeid, "phase": report.when, "outcome": report.outcome}
        )


def pytest_sessionfinish(session, exitstatus):
    """Write session outcomes and match failed tests to known integration findings."""
    if not os.environ.get("INTEGRATION_RESULTS_DIR"):
        return
    directory = Path(os.environ["INTEGRATION_RESULTS_DIR"])
    (directory / "summary.json").write_text(
        json.dumps({"exitStatus": int(exitstatus), "tests": reports}, indent=2)
    )
    findings = json.loads((Path(__file__).parents[1] / "findings.json").read_text())
    failed = [row["test"] for row in reports if row["outcome"] == "failed"]
    observed = []
    for finding in findings:
        matching = [
            test
            for test in failed
            if any(test.endswith(case) for case in finding["tests"])
        ]
        if matching:
            observed.append(
                {
                    **finding,
                    "reproduce": [
                        f"./scripts/test-integration.sh {test}" for test in matching
                    ],
                }
            )
    (directory / "bugs.json").write_text(json.dumps(observed, indent=2))
