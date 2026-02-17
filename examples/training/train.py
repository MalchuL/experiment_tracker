from __future__ import annotations

import argparse
import logging
import random
import time
from typing import Any, Optional

import httpx

from experiment_tracker_sdk import ExperimentClient
from experiment_tracker_sdk.config import load_config
from experiment_tracker_sdk.models import ExperimentStatus

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
    sdk_client: Optional[ExperimentClient] = None
    experiment_id: Optional[str] = None
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

        sdk_client = ExperimentClient(
            base_url=config.base_url, api_token=config.api_token
        )
        experiment = sdk_client.create_experiment(
            project_id=str(project["id"]),
            name=args.experiment_name,
            description="Random 1-minute training run",
            color=f"#{random.randint(0, 0xFFFFFF):06x}",
            status=ExperimentStatus.PLANNED,
        )
        experiment_id = experiment.id
        logger.info("experiment_created", extra={"experiment_id": experiment.id})

        sdk_client.update_experiment(
            experiment_id=experiment.id,
            status=ExperimentStatus.RUNNING,
            progress=0,
        )
        logger.info("experiment_started", extra={"experiment_id": experiment.id})

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
            sdk_client.log_scalars(
                experiment_id=experiment.id,
                scalars={
                    "accuracy": accuracy,
                    "loss": loss,
                    "bce_loss": bce_loss,
                },
                step=step,
                tags=["training"],
            )
            sdk_client.update_experiment(
                experiment_id=experiment.id,
                status=ExperimentStatus.RUNNING,
                progress=progress,
            )
            logger.info(
                "training_progress",
                extra={
                    "step": step,
                    "progress": progress,
                    "experiment_id": experiment.id,
                    "accuracy": accuracy,
                    "loss": loss,
                    "bce_loss": bce_loss,
                },
            )

        final_accuracy = random.uniform(0.7, 0.99)
        final_loss = random.uniform(0.1, 0.6)
        sdk_client.log_metric(
            experiment.id, name="accuracy", value=final_accuracy, step=steps
        )
        sdk_client.log_metric(
            experiment.id,
            name="loss",
            value=final_loss,
            step=steps,
            direction="minimize",
        )
        sdk_client.flush()
        logger.info(
            "scalars_logged",
            extra={
                "experiment_id": experiment.id,
                "steps": steps,
                "scalar_names": ["accuracy", "loss", "bce_loss"],
            },
        )

        sdk_client.update_experiment(
            experiment_id=experiment.id,
            status=ExperimentStatus.COMPLETE,
            progress=100,
        )
        logger.info("experiment_completed", extra={"experiment_id": experiment.id})
    except Exception:
        if sdk_client is not None and experiment_id is not None:
            try:
                sdk_client.update_experiment(
                    experiment_id=experiment_id,
                    status=ExperimentStatus.FAILED,
                )
            except Exception:
                logger.exception(
                    "failed_to_mark_experiment_failed",
                    extra={"experiment_id": experiment_id},
                )
        logger.exception("training_failed")
        raise
    finally:
        if sdk_client is not None:
            sdk_client.close()
        api_client.close()


if __name__ == "__main__":
    main()
