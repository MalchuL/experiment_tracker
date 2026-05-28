from __future__ import annotations

import argparse
import importlib.metadata
import json
import logging
import random
import subprocess
import sys
import time
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image

from experiment_tracker_sdk import (
    ExperimentStatus,
    ExpTracker,
    InitParams,
    config,
    image_data_to_png_bytes,
)

logger = logging.getLogger("training_example")


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


def _image_data_to_png_bytes(image: np.ndarray) -> bytes:
    buffer = BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    return buffer.getvalue()


def _build_checkerboard_image(
    size: int = 128,
    tile_size: int = 16,
    color_a: tuple[int, int, int] = (32, 48, 64),
    color_b: tuple[int, int, int] = (240, 196, 80),
) -> np.ndarray:
    rows, cols = np.indices((size, size))
    mask = ((rows // tile_size) + (cols // tile_size)) % 2 == 0
    image = np.empty((size, size, 3), dtype=np.uint8)
    image[mask] = color_a
    image[~mask] = color_b
    return image


def _build_large_training_text(
    args: argparse.Namespace, steps: int, duration_seconds: int
) -> str:
    header = [
        "Synthetic training run report",
        f"project={args.project_name}",
        f"experiment={args.experiment_name}",
        f"team={args.team_name or 'none'}",
        f"steps={steps}",
        f"duration_seconds={duration_seconds}",
        "",
    ]
    rows = [
        (
            f"epoch={epoch:03d} "
            f"phase={'warmup' if epoch < 10 else 'main'} "
            f"target_lr={0.001 * (1 + epoch / 100):.6f} "
            f"notes=deterministic large text payload for artifact rendering"
        )
        for epoch in range(1, 151)
    ]
    return "\n".join(header + rows) + "\n"


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


def _build_feature_tree(
    args: argparse.Namespace, steps: int, duration_seconds: int
) -> list[dict[str, Any]]:
    return [
        {
            "name": "data",
            "children": [
                {"name": "synthetic-random-images"},
                {"name": "box-blur-ground-truth"},
                {"name": "uint8-rgb-256x256-samples"},
            ],
        },
        {
            "name": "model",
            "children": [
                {"name": "demo-stochastic-metric-generator"},
                {"name": "accuracy-loss-bce-simulation"},
            ],
        },
        {
            "name": "training",
            "children": [
                {"name": f"steps-{steps}"},
                {"name": f"duration-seconds-{duration_seconds}"},
                {"name": "optimizer-random-walk"},
                {"name": "scheduler-linear-power-sweep"},
            ],
        },
        {
            "name": "logging",
            "children": [
                {"name": "scalars-accuracy-loss-bce-power-rng"},
                {"name": "sparse-scalars-accuracy-map-1-percent"},
                {"name": "final-metrics-loss-accuracy-precision-recall"},
                {"name": "at-step-image-artifacts"},
                {"name": "named-final-artifacts"},
                {"name": "direct-numpy-image-artifacts"},
                {"name": "large-at-step-text-artifacts"},
                {
                    "name": "config",
                    "children": [
                        (
                            {"name": "external-config-yaml"}
                            if args.config_path
                            else {"name": "generated-config-yaml"}
                        )
                    ],
                },
            ],
        },
    ]


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
    if config.load_config() is None:
        raise SystemExit("SDK config not found. Run `experiment-tracker init`.")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    logger.info(
        "starting_training",
        extra={"project": args.project_name, "team": args.team_name},
    )
    tracker: ExpTracker | None = None
    try:
        duration_seconds = 60
        steps = 12000
        tracker = ExpTracker.init(
            project=args.project_name,
            experiment=args.experiment_name,
            team=args.team_name,
            init_params=InitParams(
                create_team_if_not_exists=True,
                create_project_if_not_exists=True,
                create_experiment_if_not_exists=True,
            ),
        )
        experiment_id = str(tracker.experiment_id)
        logger.info(
            "tracker_initialized",
            extra={
                "project_id": str(tracker.project_id),
                "experiment_id": experiment_id,
            },
        )

        tracker.features(_build_feature_tree(args, steps, duration_seconds))
        tracker.tags("training-example")
        tracker.status(ExperimentStatus.RUNNING)
        tracker.progress(0)
        tracker.color(f"#{random.randint(0, 16777215):06x}")
        logger.info("experiment_started", extra={"experiment_id": experiment_id})

        step_seconds = duration_seconds / steps
        start_time = time.time()
        # Scalar tag "power": magnitude sweep from very large to very small values.
        power_exp_high = 15.0
        power_exp_low = -15.0
        scalar_log_step = max(1, steps // 100)

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
        tracker.log_final_yaml(
            "run config_helper/asda ! dsf:",
            {
                "run": {
                    "project_name": args.project_name,
                    "experiment_name": args.experiment_name,
                    "team_name": args.team_name,
                    "steps": steps,
                    "duration_seconds": duration_seconds,
                }
            },
        )
        installed_packages = _capture_installed_packages()
        tracker.log_final_artifact(
            "python packages",
            installed_packages,
            stored_filepath="final/pip-freeze.txt",
            default_content_type="text/plain",
        )
        tracker.log_final_text(
            "python_packages_helper",
            installed_packages,
        )
        # Two final artifact image paths: local PNG bytes and public SDK helper.
        final_demo = np.random.randint(0, 256, size=(128, 128, 3), dtype=np.uint8)
        final_checkerboard = _build_checkerboard_image()
        final_demo_png = _image_data_to_png_bytes(final_demo)
        tracker.log_final_artifact(
            "final_demo_image",
            final_demo_png,
            stored_filepath="final/demo_image_primary.png",
            default_content_type="image/png",
            default_extension=".png",
        )
        tracker.log_final_image(
            "final_demo_image_helper",
            final_demo_png,
            stored_filepath="final/demo_image_helper.png",
        )
        tracker.log_final_image(
            "final_checkerboard_numpy",
            final_checkerboard,
            stored_filepath="final/checkerboard_numpy.png",
        )
        tracker.log_final_artifact(
            "final_demo_image",
            image_data_to_png_bytes(_smooth_image(final_demo)),
            stored_filepath="final/demo_image_secondary.png",
            default_content_type="image/png",
            default_extension=".png",
        )
        summary_payload = {
            "experiment_id": experiment_id,
            "planned_steps": steps,
            "when": "training_start",
        }
        tracker.log_final_artifact(
            "training_summary_json",
            json.dumps(summary_payload, indent=2),
            stored_filepath="final/training_summary_primary.json",
            default_content_type="application/json",
            default_extension=".json",
        )
        tracker.log_final_json(
            "training_summary_json_helper",
            {**summary_payload, "path_variant": "helper"},
            stored_filepath="final/training_summary_helper.json",
        )
        tracker.log_final_artifact(
            "training_summary_json",
            json.dumps(
                {**summary_payload, "path_variant": "secondary"},
                indent=2,
            ),
            stored_filepath="final/training_summary_secondary.json",
            default_content_type="application/json",
            default_extension=".json",
        )
        logger.info("final_artifacts_logged", extra={"experiment_id": experiment_id})

        accuracy = random.uniform(0.6, 0.99)
        mean_average_precision = random.uniform(0.45, 0.75)
        loss = random.uniform(0.1, 1.2)
        bce_loss = random.uniform(0.05, 0.9)

        for step in range(1, steps + 1):
            time.sleep(step_seconds)
            elapsed = time.time() - start_time
            progress = min(100, int((elapsed / duration_seconds) * 100))

            # Simulate training metrics and log several scalar values per step.
            accuracy += random.uniform(-0.1, 0.1)
            mean_average_precision += random.uniform(-0.05, 0.05)
            loss += random.uniform(-0.1, 0.1)
            bce_loss += random.uniform(-0.1, 0.1)
            accuracy = max(0.0, min(1.0, accuracy))
            mean_average_precision = max(0.0, min(1.0, mean_average_precision))
            if step % scalar_log_step == 0 or step == steps:
                tracker.add_scalar("accuracy", accuracy, global_step=step // 100)
                tracker.add_scalar(
                    "mAP", mean_average_precision, global_step=step // 100
                )
            tracker.add_scalar("loss", loss, global_step=step)
            tracker.add_scalar("bce_loss", bce_loss, global_step=step)
            if steps > 1:
                power_t = (step - 1) / (steps - 1)
            else:
                power_t = 0.0
            power_exponent = power_exp_high + power_t * (power_exp_low - power_exp_high)
            tracker.add_scalar("power", 10.0**power_exponent, global_step=step)
            tracker.add_scalar(
                "rng",
                float("NaN") if step % 3 == 0 else float(random.random()),
                global_step=step,
            )
            if step % 400 == 0:
                tracker.add_text(
                    "training_note",
                    (
                        f"step={step} progress={progress}% "
                        f"loss={loss:.4f} accuracy={accuracy:.4f}"
                    ),
                    global_step=step,
                )
                tracker.add_text(
                    "large_training_report",
                    _build_large_training_text(args, steps, duration_seconds),
                    global_step=step,
                )
            if step % 500 == 0:
                # Direct image logging path: pass HWC uint8 arrays to the tracker.
                noise_image = np.random.randint(
                    0, 256, size=(256, 256, 3), dtype=np.uint8
                )
                checkerboard_image = _build_checkerboard_image(
                    size=256,
                    tile_size=16,
                    color_a=(16, 96, 80),
                    color_b=(240, 220, 96),
                )
                tracker.add_image("generated", noise_image, global_step=step)
                tracker.add_image("gt", _smooth_image(noise_image), global_step=step)
                tracker.add_image(
                    "checkerboard_numpy",
                    checkerboard_image,
                    global_step=step,
                )
            tracker.progress(progress)
            logger.info(
                "training_progress",
                extra={
                    "step": step,
                    "progress": progress,
                    "experiment_id": experiment_id,
                    "accuracy": accuracy,
                    "mAP": mean_average_precision,
                    "loss": loss,
                    "bce_loss": bce_loss,
                },
            )

        final_metrics = {
            "loss": random.uniform(0.1, 0.6),
            "accuracy": random.uniform(0.7, 0.99),
            "mAP": random.uniform(0.55, 0.95),
            "precision": random.uniform(0.6, 0.99),
            "recall": random.uniform(0.6, 0.99),
        }
        for metric_name, metric_value in final_metrics.items():
            tracker.add_metric(
                name=metric_name,
                value=metric_value,
                label="final",
            )

        # Metrics (Postgres): one row per (name, label); log discrete magnitudes
        # like the scalar sweep.
        power_metric_names: list[str] = []
        for exp in range(15, -16, -1):
            name = f"e{exp:+d}"
            power_metric_names.append(name)
            tracker.add_metric(
                name=name,
                value=float(10**exp),
                label="power",
            )

        summary_payload = {
            "experiment_id": experiment_id,
            "steps": steps,
            "final_metrics": final_metrics,
        }
        tracker.log_final_artifact(
            "training_summary_json",
            json.dumps(summary_payload, indent=2),
            stored_filepath="final/training_summary_postrun_primary.json",
            default_content_type="application/json",
            default_extension=".json",
        )
        tracker.log_final_json(
            "training_summary_json_helper",
            {**summary_payload, "path_variant": "postrun_helper"},
            stored_filepath="final/training_summary_postrun_helper.json",
        )
        tracker.log_final_artifact(
            "training_summary_json",
            json.dumps(
                {**summary_payload, "path_variant": "secondary"},
                indent=2,
            ),
            stored_filepath="final/training_summary_postrun_secondary.json",
            default_content_type="application/json",
            default_extension=".json",
        )

        tracker.flush()
        logger.info(
            "training_logged",
            extra={
                "experiment_id": experiment_id,
                "steps": steps,
                "scalar_names": [
                    "accuracy",
                    "mAP",
                    "loss",
                    "bce_loss",
                    "power",
                ],
                "metric_names": list(final_metrics.keys()) + power_metric_names,
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
            try:
                tracker.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
