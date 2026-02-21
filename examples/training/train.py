from __future__ import annotations

import argparse
import logging
import random
import time
from typing import Any, Optional

import httpx

from experiment_tracker_sdk import ExpTracker
from experiment_tracker_sdk.client import ExperimentStatus
from experiment_tracker_sdk.config import load_config

logger = logging.getLogger("training_example")


def _get_api_client(base_url: str, api_token: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url.rstrip("/"),
        headers={"Authorization": f"Bearer {api_token}"},
        timeout=10.0,
    )


def _list_projects(client: httpx.Client) -> list[dict[str, Any]]:
    response = client.get("/api/projects")
    response.raise_for_status()
    return response.json()


def _find_team_id_from_projects(
    projects: list[dict[str, Any]], team_name: str
) -> Optional[str]:
    for project in projects:
        team = project.get("team")
        if team and team.get("name") == team_name:
            return str(team.get("id"))
    return None


def _create_team(client: httpx.Client, team_name: str) -> str:
    response = client.post(
        "/api/teams",
        json={"name": team_name, "description": "SDK training example team"},
    )
    response.raise_for_status()
    return str(response.json()["id"])


def _find_project(
    projects: list[dict[str, Any]], project_name: str, team_name: Optional[str]
) -> Optional[dict[str, Any]]:
    for project in projects:
        if project.get("name") != project_name:
            continue
        team = project.get("team")
        if team_name is None and team is None:
            return project
        if team_name is not None and team and team.get("name") == team_name:
            return project
    return None


def _create_project(
    client: httpx.Client, project_name: str, team_id: Optional[str]
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": project_name,
        "description": "SDK training example project",
    }
    if team_id:
        payload["teamId"] = team_id
    response = client.post("/api/projects", json=payload)
    response.raise_for_status()
    return response.json()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SDK training example")
    parser.add_argument("--project-name", default="SDK Training")
    parser.add_argument("--experiment-name", default="SDK Training Run")
    parser.add_argument("--team-name", default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = load_config()
    if config is None:
        raise SystemExit("SDK config not found. Run `experiment-tracker init`.")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    logger.info(
        "starting_training",
        extra={"project": args.project_name, "team": args.team_name},
    )
    api_client = _get_api_client(config.base_url, config.api_token)
    tracker: Optional[ExpTracker] = None
    try:
        projects = _list_projects(api_client)
        team_id = None
        if args.team_name:
            team_id = _find_team_id_from_projects(projects, args.team_name)
            if team_id is None:
                logger.info("team_not_found_creating", extra={"team": args.team_name})
                team_id = _create_team(api_client, args.team_name)
                logger.info("team_created", extra={"team_id": team_id})
                projects = _list_projects(api_client)

        project = _find_project(projects, args.project_name, args.team_name)
        if project is None:
            logger.info(
                "project_not_found_creating", extra={"project": args.project_name}
            )
            project = _create_project(api_client, args.project_name, team_id)
            logger.info("project_created", extra={"project_id": project["id"]})
        else:
            logger.info("project_found", extra={"project_id": project["id"]})

        tracker = ExpTracker.init(
            project=str(project["id"]),
            experiment=args.experiment_name,
        )
        tracker.
        experiment_id = str(tracker.experiment_id)
        logger.info("experiment_created", extra={"experiment_id": experiment_id})

        tracker.tags("training-example")
        tracker.status(ExperimentStatus.RUNNING)
        tracker.progress(0)
        logger.info("experiment_started", extra={"experiment_id": experiment_id})

        duration_seconds = 60
        steps = 12
        step_seconds = duration_seconds / steps
        start_time = time.time()

        for step in range(1, steps + 1):
            time.sleep(step_seconds)
            elapsed = time.time() - start_time
            progress = min(100, int((elapsed / duration_seconds) * 100))

            # Simulate training metrics and log several scalar values per step.
            accuracy = random.uniform(0.6, 0.99)
            loss = random.uniform(0.1, 1.2)
            bce_loss = random.uniform(0.05, 0.9)
            tracker.add_scalar("accuracy", accuracy, global_step=step)
            tracker.add_scalar("loss", loss, global_step=step)
            tracker.add_scalar("bce_loss", bce_loss, global_step=step)
            tracker.progress(progress)
            logger.info(
                "training_progress",
                extra={
                    "step": step,
                    "progress": progress,
                    "experiment_id": experiment_id,
                    "accuracy": accuracy,
                    "loss": loss,
                    "bce_loss": bce_loss,
                },
            )

        final_accuracy = random.uniform(0.7, 0.99)
        final_loss = random.uniform(0.1, 0.6)
        tracker.add_scalar("final_accuracy", final_accuracy, global_step=steps)
        tracker.add_scalar("final_loss", final_loss, global_step=steps)
        tracker.flush()
        logger.info(
            "scalars_logged",
            extra={
                "experiment_id": experiment_id,
                "steps": steps,
                "scalar_names": [
                    "accuracy",
                    "loss",
                    "bce_loss",
                    "final_accuracy",
                    "final_loss",
                ],
            },
        )

        tracker.status(ExperimentStatus.COMPLETE)
        tracker.progress(100)
        logger.info("experiment_completed", extra={"experiment_id": experiment_id})
    except Exception:
        if tracker is not None:
            try:
                tracker.status(ExperimentStatus.FAILED)
            except Exception:
                logger.exception(
                    "failed_to_mark_experiment_failed",
                    extra={"experiment_id": str(tracker.experiment_id)},
                )
        logger.exception("training_failed")
        raise
    finally:
        if tracker is not None:
            tracker.close()
        api_client.close()


if __name__ == "__main__":
    main()
