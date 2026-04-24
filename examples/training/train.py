from __future__ import annotations

import argparse
import importlib.metadata
import logging
import random
import subprocess
import sys
import time
from typing import Any, Optional

import httpx
import numpy as np

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
    response = client.get("/projects")
    response.raise_for_status()
    payload = response.json()
    return payload["data"]


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
        "/teams",
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
    response = client.post("/projects", json=payload)
    response.raise_for_status()
    return response.json()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SDK training example")
    parser.add_argument("--project-name", default="SDK Training")
    parser.add_argument("--experiment-name", default="SDK Training Run")
    parser.add_argument("--team-name", default=None)
    parser.add_argument(
        "--config-path",
        default=None,
        help="Optional path to YAML config file to upload as final artifact",
    )
    return parser.parse_args()


def _smooth_image(image: np.ndarray, kernel_size: int = 7) -> np.ndarray:
    """Simple box blur for demo GT image generation."""
    if kernel_size < 1 or kernel_size % 2 == 0:
        raise ValueError("kernel_size must be a positive odd integer")
    if image.ndim != 3 or image.shape[2] not in (3, 4):
        raise ValueError("Expected HWC image with 3 or 4 channels")

    height, width, channels = image.shape
    pad = kernel_size // 2
    padded = np.pad(
        image.astype(np.float32),
        ((pad, pad), (pad, pad), (0, 0)),
        mode="reflect",
    )
    smoothed = np.zeros((height, width, channels), dtype=np.float32)
    for dy in range(kernel_size):
        for dx in range(kernel_size):
            smoothed += padded[dy : dy + height, dx : dx + width, :]
    smoothed /= float(kernel_size * kernel_size)
    return np.clip(smoothed, 0, 255).astype(np.uint8)


def _build_run_config_yaml(
    args: argparse.Namespace, steps: int, duration_seconds: int
) -> str:
    lines = [
        "run:",
        f"  project_name: {args.project_name}",
        f"  experiment_name: {args.experiment_name}",
        f"  team_name: {args.team_name or 'null'}",
        f"  steps: {steps}",
        f"  duration_seconds: {duration_seconds}",
    ]
    return "\n".join(lines) + "\n"


def _capture_installed_packages() -> str:
    commands = (
        ["uv", "pip", "freeze"],
        [sys.executable, "-m", "pip", "freeze"],
    )
    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.strip()
            if output:
                return output + "\n"
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "packages_capture_command_failed",
                extra={"command": command, "error": str(exc)},
            )

    # Fallback: gather installed distributions directly from runtime metadata.
    try:
        packages: list[str] = []
        for dist in importlib.metadata.distributions():
            package_name = (
                dist.metadata.get("Name")
                or dist.metadata.get("name")
                or "unknown-package"
            )
            packages.append(f"{package_name}=={dist.version}")
        packages.sort()
        if packages:
            return "\n".join(packages) + "\n"
    except Exception as exc:  # noqa: BLE001
        logger.warning("packages_capture_metadata_failed", extra={"error": str(exc)})

    return "package-capture-unavailable\n"


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
        experiment_id = str(tracker.experiment_id)
        logger.info("experiment_created", extra={"experiment_id": experiment_id})

        tracker.tags("training-example")
        tracker.status(ExperimentStatus.RUNNING)
        tracker.progress(0)
        tracker.color(f"#{random.randint(0, 16777215):06x}")
        logger.info("experiment_started", extra={"experiment_id": experiment_id})

        duration_seconds = 60
        steps = 120
        step_seconds = duration_seconds / steps
        start_time = time.time()

        if args.config_path:
            with open(args.config_path, encoding="utf-8") as config_file:
                config_yaml = config_file.read()
        else:
            config_yaml = _build_run_config_yaml(args, steps, duration_seconds)
        tracker.log_final_artifact(
            "run_config",
            config_yaml,
            stored_filepath="final/config.yaml",
            default_content_type="application/x-yaml",
        )
        tracker.log_final_artifact(
            "python_packages",
            _capture_installed_packages(),
            stored_filepath="final/pip-freeze.txt",
            default_content_type="text/plain",
        )
        logger.info("final_artifacts_logged", extra={"experiment_id": experiment_id})

        accuracy = random.uniform(0.6, 0.99)
        loss = random.uniform(0.1, 1.2)
        bce_loss = random.uniform(0.05, 0.9)

        for step in range(1, steps + 1):
            time.sleep(step_seconds)
            elapsed = time.time() - start_time
            progress = min(100, int((elapsed / duration_seconds) * 100))

            # Simulate training metrics and log several scalar values per step.
            accuracy += random.uniform(-0.1, 0.1)
            loss += random.uniform(-0.1, 0.1)
            bce_loss += random.uniform(-0.1, 0.1)
            tracker.add_scalar("accuracy", accuracy, global_step=step)
            tracker.add_scalar("loss", loss, global_step=step)
            tracker.add_scalar("bce_loss", bce_loss, global_step=step)
            tracker.add_scalar(
                "rng",
                float("NaN") if step % 3 == 0 else float(random.random()),
                global_step=step,
            )
            if step % 20 == 0:
                # Random demo image (HWC, uint8) for object logging examples.
                noise_image = np.random.randint(
                    0, 256, size=(256, 256, 3), dtype=np.uint8
                )
                tracker.add_image("generated", noise_image, global_step=step)
                tracker.add_image("gt", _smooth_image(noise_image), global_step=step)
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

        final_metrics = {
            "loss": random.uniform(0.1, 0.6),
            "accuracy": random.uniform(0.7, 0.99),
            "precision": random.uniform(0.6, 0.99),
            "recall": random.uniform(0.6, 0.99),
        }
        for metric_name, metric_value in final_metrics.items():
            tracker.add_metric(
                name=metric_name,
                value=metric_value,
                step=steps,
                label="final",
            )
        tracker.flush()
        logger.info(
            "training_logged",
            extra={
                "experiment_id": experiment_id,
                "steps": steps,
                "scalar_names": [
                    "accuracy",
                    "loss",
                    "bce_loss",
                ],
                "metric_names": list(final_metrics.keys()),
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
