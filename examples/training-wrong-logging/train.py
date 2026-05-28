from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image

from experiment_tracker_sdk import (
    ExperimentStatus,
    ExpTracker,
    InitParams,
    config,
)

logger = logging.getLogger("wrong_logging_example")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SDK wrong logging example")
    parser.add_argument("--project-name", default="SDK Wrong Logging")
    parser.add_argument("--experiment-name", default="Wrong Artifact Inputs")
    parser.add_argument("--team-name", default=None)
    return parser.parse_args()


def _checkerboard_image(
    size: int = 64,
    tile_size: int = 8,
    color_a: tuple[int, int, int] = (24, 72, 96),
    color_b: tuple[int, int, int] = (240, 192, 64),
) -> np.ndarray:
    rows, cols = np.indices((size, size))
    mask = ((rows // tile_size) + (cols // tile_size)) % 2 == 0
    image = np.empty((size, size, 3), dtype=np.uint8)
    image[mask] = color_a
    image[~mask] = color_b
    return image


def _png_bytes(image: np.ndarray) -> bytes:
    buffer = BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    return buffer.getvalue()


def _features() -> list[dict[str, Any]]:
    return [
        {
            "name": "wrong-logging",
            "children": [
                {"name": "text-under-image-helper"},
                {"name": "image-under-text-helper"},
                {"name": "invalid-json-as-json"},
                {"name": "generic-artifact-mime-mismatch"},
                {"name": "expected-step-helper-errors"},
            ],
        }
    ]


def _record_attempt(
    tracker: ExpTracker,
    *,
    name: str,
    step: int,
    action: Callable[[], None],
) -> dict[str, str]:
    try:
        action()
    except Exception as exc:  # noqa: BLE001
        status = {
            "name": name,
            "result": "expected_error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        log_extra = {
            "attempt_name": status["name"],
            "result": status["result"],
            "error_type": status["error_type"],
            "error": status["error"],
        }
        logger.info("wrong_logging_expected_error", extra=log_extra)
    else:
        status = {
            "name": name,
            "result": "logged",
            "error_type": "",
            "error": "",
        }
        log_extra = {
            "attempt_name": status["name"],
            "result": status["result"],
            "error_type": status["error_type"],
            "error": status["error"],
        }
        logger.info("wrong_logging_logged", extra=log_extra)

    tracker.add_text(
        f"wrong_logging_attempt/{name}",
        json.dumps(status, indent=2),
        global_step=step,
    )
    return status


def _log_scalars(tracker: ExpTracker) -> None:
    for step in range(1, 8):
        normalized_step = step / 7
        tracker.add_scalar(
            "wrong_logging/loss",
            round(1.0 / (step + 0.5), 6),
            global_step=step,
        )
        tracker.add_scalar(
            "wrong_logging/accuracy",
            round(0.48 + normalized_step * 0.34, 6),
            global_step=step,
        )
        tracker.add_scalar(
            "wrong_logging/artifact_mismatch_score",
            float((step * 3) % 5),
            global_step=step,
        )


def main() -> None:
    args = _parse_args()
    if config.load_config() is None:
        raise SystemExit("SDK config not found. Run `experiment-tracker init`.")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    tracker: ExpTracker | None = None
    try:
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
        tracker.features(_features())
        tracker.tags("wrong-logging-example")
        tracker.status(ExperimentStatus.RUNNING)
        tracker.progress(0)
        _log_scalars(tracker)

        image = _checkerboard_image()
        image_bytes = _png_bytes(image)
        statuses: list[dict[str, str]] = []

        statuses.append(
            _record_attempt(
                tracker,
                name="step_text_as_image",
                step=1,
                action=lambda: tracker.add_image(
                    "text_as_image",
                    "this is text, not image data",
                    global_step=1,
                ),
            )
        )
        statuses.append(
            _record_attempt(
                tracker,
                name="step_image_as_text",
                step=2,
                action=lambda: tracker.add_text(
                    "image_array_as_text",
                    image,  # type: ignore[arg-type]
                    global_step=2,
                ),
            )
        )

        tracker.log_final_image(
            "final_text_logged_as_image",
            "plain text payload logged with image helper",
        )
        tracker.log_final_text(
            "final_image_bytes_logged_as_text",
            image_bytes,
        )
        tracker.log_final_json(
            "final_invalid_json_string",
            "{not valid json, but labeled as application/json}",
        )
        tracker.log_final_yaml(
            "final_png_bytes_logged_as_yaml",
            image_bytes,
        )
        tracker.log_final_artifact(
            "generic_text_labeled_as_jpeg",
            b"not a jpeg payload",
            default_content_type="image/jpeg",
            default_extension=".jpg",
        )
        tracker.log_final_artifact(
            "generic_png_labeled_as_text",
            image_bytes,
            default_content_type="text/plain",
            default_extension=".txt",
        )
        tracker.log_final_json(
            "wrong_logging_attempt_summary",
            {"attempts": statuses},
        )

        tracker.progress(100)
        tracker.status(ExperimentStatus.COMPLETE)
        tracker.flush()
        logger.info("wrong_logging_example_complete")
    except Exception:
        if tracker is not None:
            try:
                tracker.status(ExperimentStatus.FAILED)
                tracker.flush()
            except Exception as cleanup_exc:  # noqa: BLE001
                logger.warning(
                    "failed_to_mark_experiment_failed",
                    extra={"error": str(cleanup_exc)},
                )
        raise
    finally:
        if tracker is not None:
            try:
                tracker.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
