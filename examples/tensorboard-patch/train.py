from __future__ import annotations

import argparse
import logging
import random
import time
from pathlib import Path

import numpy as np
from tensorboardX import SummaryWriter

from experiment_tracker_sdk import (
    ExperimentStatus,
    ExpTracker,
    InitParams,
    config,
    monkey_patch_tensorboard,
)

logger = logging.getLogger("tensorboard_patch_example")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Log synthetic metrics via TensorBoardX and mirror them to the tracker.",
    )
    parser.add_argument("--project-name", default="TensorBoard Patch")
    parser.add_argument("--experiment-name", default="TensorBoard Patch Run")
    parser.add_argument("--team-name", default=None)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.05,
        help="Seconds between steps (0 for a fast smoke test).",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("runs/tensorboard-patch"),
        help="Local TensorBoard event directory.",
    )
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def _checkerboard_image(size: int = 64) -> np.ndarray:
    tile_size = 8
    rows, cols = np.indices((size, size))
    mask = ((rows // tile_size) + (cols // tile_size)) % 2 == 0
    image = np.empty((size, size, 3), dtype=np.uint8)
    image[mask] = (24, 72, 96)
    image[~mask] = (240, 192, 64)
    return image


def main() -> None:
    args = _parse_args()
    if config.load_config() is None:
        raise SystemExit("SDK config not found. Run `experiment-tracker init`.")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    random.seed(args.seed)
    np.random.seed(args.seed)

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
        monkey_patch_tensorboard(tracker)

        tracker.tags("tensorboard-patch-example")
        tracker.status(ExperimentStatus.RUNNING)
        tracker.progress(0)

        logger.info(
            "tracker_ready",
            extra={
                "project_id": str(tracker.project_id),
                "experiment_id": str(tracker.experiment_id),
                "log_dir": str(args.log_dir),
            },
        )

        loss = 1.0
        accuracy = 0.5
        args.log_dir.mkdir(parents=True, exist_ok=True)

        with SummaryWriter(logdir=str(args.log_dir)) as writer:
            writer.add_hparams(
                {"lr": args.lr, "steps": args.steps},
                {"hparam/final_accuracy": 0.0},
            )

            for step in range(1, args.steps + 1):
                loss *= random.uniform(0.92, 0.98)
                accuracy = min(0.99, accuracy + random.uniform(0.0, 0.03))

                writer.add_scalar("train/loss", loss, step)
                writer.add_scalar("train/accuracy", accuracy, step)

                if step % 10 == 0:
                    writer.add_image(
                        "train/checkerboard",
                        _checkerboard_image(),
                        step,
                        dataformats="HWC",
                    )
                    writer.add_histogram(
                        "train/noise",
                        np.random.randn(256),
                        step,
                        bins=16,
                    )

                tracker.progress(int(100 * step / args.steps))
                if args.sleep > 0:
                    time.sleep(args.sleep)

        tracker.status(ExperimentStatus.COMPLETE)
        tracker.flush()
        logger.info("tensorboard_patch_example_complete")
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
