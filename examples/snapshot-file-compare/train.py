from __future__ import annotations

import argparse
import json
import logging
import random
import time
from pathlib import Path

from experiment_tracker_sdk import ExperimentStatus, ExpTracker, InitParams, config

logger = logging.getLogger("snapshot_file_compare")

SNAPSHOT_INCLUDED_FILE_COUNT = 30

VARIANT_DEFAULTS = {
    "baseline": {"learning_rate": 0.012, "dropout": 0.05, "layers": [64, 32]},
    "dropout": {"learning_rate": 0.010, "dropout": 0.35, "layers": [64, 32]},
    "wide": {"learning_rate": 0.008, "dropout": 0.10, "layers": [128, 64, 32]},
}


def parse_args() -> argparse.Namespace:
    """Parse CLI options for the snapshot file-compare example.

    Args:
        None. Arguments are read from ``sys.argv`` by ``argparse``.

    Returns:
        Namespace containing project, experiment, variant, randomization,
        workspace, step-count, and pacing options for the example run.
    """
    parser = argparse.ArgumentParser(
        description="Generate training files and log a snapshot for Compare."
    )
    parser.add_argument("--project-name", default="Snapshot File Compare")
    parser.add_argument("--experiment-name", default=None)
    parser.add_argument("--team-name", default=None)
    parser.add_argument(
        "--variant",
        choices=sorted(VARIANT_DEFAULTS),
        default="baseline",
        help="Deterministic model/config variant to generate.",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument(
        "--random-training",
        action="store_true",
        help="Use a fresh random seed and randomly perturb config/code outputs.",
    )
    parser.add_argument(
        "--workspace",
        default="training_files",
        help="Directory to generate and snapshot.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Optional seconds to sleep between steps for visible live logging.",
    )
    parser.add_argument(
        "--file-count",
        type=int,
        default=SNAPSHOT_INCLUDED_FILE_COUNT,
        help=(
            "Number of snapshot-included files to generate "
            f"(default: {SNAPSHOT_INCLUDED_FILE_COUNT})."
        ),
    )
    return parser.parse_args()


def build_run_config(args: argparse.Namespace, rng: random.Random) -> dict:
    """Build the synthetic training configuration for one example run.

    Args:
        args: Parsed CLI arguments containing the selected variant and
            random-training flag.
        rng: Random number generator used for reproducible or randomized config
            perturbations.

    Returns:
        Dictionary of model and optimizer settings that will be written to the
        snapshot and used during metric generation.
    """
    base = dict(VARIANT_DEFAULTS[args.variant])
    if args.random_training:
        base["learning_rate"] = round(rng.uniform(0.004, 0.02), 5)
        base["dropout"] = round(rng.uniform(0.0, 0.5), 3)
        layer_count = rng.randint(2, 4)
        base["layers"] = [rng.choice([32, 64, 96, 128]) for _ in range(layer_count)]

    return {
        "variant": args.variant,
        "random_training": args.random_training,
        "seed": args.seed,
        "steps": args.steps,
        "optimizer": (
            rng.choice(["adamw", "sgd", "lion"]) if args.random_training else "adamw"
        ),
        "learning_rate": base["learning_rate"],
        "dropout": base["dropout"],
        "layers": base["layers"],
        "batch_size": rng.choice([16, 32, 64]) if args.random_training else 32,
    }


def write_training_files(
    workspace: Path,
    run_config: dict,
    history: list[dict[str, float]],
    final_accuracy: float,
    final_loss: float,
    *,
    file_count: int = SNAPSHOT_INCLUDED_FILE_COUNT,
) -> None:
    """Write synthetic source, config, metric, and report files to snapshot.

    Args:
        workspace: Directory where the example training tree should be created.
        run_config: Configuration dictionary produced by ``build_run_config``.
        history: Per-step metric rows from ``run_training``.
        final_accuracy: Final accuracy value written into reports/checkpoints.
        final_loss: Final loss value written into reports/checkpoints.
        file_count: Target number of files included in the snapshot (ignored and
            cache files do not count toward this total).

    Returns:
        None. The function creates or overwrites files under ``workspace``.
    """
    if file_count < 1:
        raise ValueError("file_count must be at least 1")

    workspace.mkdir(parents=True, exist_ok=True)
    for subdir in (
        "src",
        "src/modules",
        "src/utils",
        "configs",
        "configs/overrides",
        "reports",
        "reports/shards",
        "checkpoints",
        "checkpoints/meta",
        "logs",
        "cache",
    ):
        (workspace / subdir).mkdir(parents=True, exist_ok=True)

    (workspace / "configs" / "training.json").write_text(
        json.dumps(run_config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    layer_lines = "\n".join(
        f"        self.layer_{index} = Dense({width})"
        for index, width in enumerate(run_config["layers"], start=1)
    )
    (workspace / "src" / "model.py").write_text(
        "\n".join(
            [
                "class SyntheticModel:",
                "    def __init__(self):",
                f"        self.variant = {run_config['variant']!r}",
                f"        self.dropout = {run_config['dropout']!r}",
                layer_lines,
                "",
                "    def forward(self, batch):",
                "        return sum(batch) / max(len(batch), 1)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    metric_rows = ["step,loss,accuracy"]
    for row in history:
        metric_rows.append(
            f"{int(row['step'])},{row['loss']:.6f},{row['accuracy']:.6f}"
        )
    (workspace / "reports" / "metrics.csv").write_text(
        "\n".join(metric_rows) + "\n",
        encoding="utf-8",
    )

    (workspace / "reports" / "summary.md").write_text(
        "\n".join(
            [
                "# Synthetic Training Summary",
                "",
                f"- Variant: `{run_config['variant']}`",
                f"- Random training: `{run_config['random_training']}`",
                f"- Optimizer: `{run_config['optimizer']}`",
                f"- Learning rate: `{run_config['learning_rate']}`",
                f"- Dropout: `{run_config['dropout']}`",
                f"- Final loss: `{final_loss:.6f}`",
                f"- Final accuracy: `{final_accuracy:.6f}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (workspace / "checkpoints" / "latest.txt").write_text(
        "\n".join(
            [
                "synthetic checkpoint",
                f"variant={run_config['variant']}",
                f"accuracy={final_accuracy:.6f}",
                f"loss={final_loss:.6f}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    # These files demonstrate .exp_tracker_ignore exclusions.
    (workspace / "logs" / "debug.log").write_text(
        "ignored debug log\n", encoding="utf-8"
    )
    (workspace / "cache" / "activations.tmp").write_text(
        "ignored cache payload\n", encoding="utf-8"
    )

    core_file_count = 5
    extra_templates = [
        (
            "src/modules/module_{index:02d}.py",
            lambda index: "\n".join(
                [
                    f'"""Synthetic module {index:02d}."""',
                    "",
                    f"VARIANT = {run_config['variant']!r}",
                    f"LEARNING_RATE = {run_config['learning_rate']!r}",
                    f"DROPOUT = {run_config['dropout']!r}",
                    "",
                    f"def forward_{index}(features):",
                    f"    return features * {run_config['learning_rate']}",
                    "",
                ]
            ),
        ),
        (
            "src/utils/helper_{index:02d}.py",
            lambda index: "\n".join(
                [
                    f"OPTIMIZER = {run_config['optimizer']!r}",
                    f"BATCH_SIZE = {run_config['batch_size']!r}",
                    "",
                    f"def scale_{index}(value):",
                    f"    return value / max({run_config['batch_size']}, 1)",
                    "",
                ]
            ),
        ),
        (
            "configs/overrides/override_{index:02d}.json",
            lambda index: json.dumps(
                {
                    "index": index,
                    "variant": run_config["variant"],
                    "learning_rate": run_config["learning_rate"],
                    "dropout": run_config["dropout"],
                    "batch_size": run_config["batch_size"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        ),
        (
            "reports/shards/shard_{index:02d}.csv",
            lambda index: "\n".join(
                [
                    "step,loss,accuracy,shard",
                    *(
                        f"{int(row['step'])},{row['loss']:.6f},"
                        f"{row['accuracy']:.6f},{index}"
                        for row in history[index :: max(len(history) // 4, 1)][:4]
                    ),
                ]
            )
            + "\n",
        ),
        (
            "checkpoints/meta/meta_{index:02d}.txt",
            lambda index: "\n".join(
                [
                    f"checkpoint-meta-{index:02d}",
                    f"variant={run_config['variant']}",
                    f"optimizer={run_config['optimizer']}",
                    f"accuracy={final_accuracy:.6f}",
                    f"loss={final_loss:.6f}",
                ]
            )
            + "\n",
        ),
    ]

    extra_needed = max(0, file_count - core_file_count)
    for extra_index in range(extra_needed):
        relative_path, content_builder = extra_templates[
            extra_index % len(extra_templates)
        ]
        file_index = extra_index // len(extra_templates) + 1
        target_path = workspace / relative_path.format(index=file_index)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content_builder(file_index), encoding="utf-8")


def run_training(
    tracker: ExpTracker,
    run_config: dict,
    *,
    steps: int,
    sleep_seconds: float,
    rng: random.Random,
) -> tuple[list[dict[str, float]], float, float]:
    """Run a deterministic synthetic training loop and log scalar metrics.

    Args:
        tracker: Initialized experiment tracker used for scalar/progress logs.
        run_config: Model and optimizer settings controlling metric evolution.
        steps: Number of synthetic training steps to emit.
        sleep_seconds: Optional delay between steps for live-demo visibility.
        rng: Random generator used for repeatable metric noise.

    Returns:
        Tuple of metric history, final accuracy, and final loss.
    """
    loss = 1.2 + rng.random() * 0.2
    accuracy = 0.35 + rng.random() * 0.05
    history: list[dict[str, float]] = []
    lr = float(run_config["learning_rate"])
    dropout = float(run_config["dropout"])

    for step in range(1, steps + 1):
        noise = rng.uniform(-0.015, 0.015)
        loss = max(0.02, loss * (0.965 + dropout * 0.015) - lr * 0.9 + noise)
        accuracy = min(
            0.995,
            accuracy + lr * 1.6 - dropout * 0.01 + rng.random() * 0.01,
        )
        history.append({"step": float(step), "loss": loss, "accuracy": accuracy})
        tracker.add_scalar("loss", loss, step)
        tracker.add_scalar("accuracy", accuracy, step)
        tracker.add_scalar("learning_rate", lr, step)
        tracker.add_scalar("dropout", dropout, step)
        tracker.progress(min(99, int(step / steps * 100)))
        if sleep_seconds:
            time.sleep(sleep_seconds)

    return history, accuracy, loss


def main() -> None:
    """Run the snapshot file-compare example end to end.

    Args:
        None. Runtime behavior is controlled by CLI arguments and SDK config.

    Returns:
        None. The function logs metrics, writes files, records a snapshot, and
        closes the tracker before exiting.
    """
    args = parse_args()
    if config.load_config() is None:
        raise SystemExit("SDK config not found. Run `experiment-tracker init`.")

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s - %(message)s",
    )

    seed = (
        random.SystemRandom().randint(1, 2**31 - 1)
        if args.random_training
        else args.seed
    )
    rng = random.Random(seed)
    args.seed = seed
    experiment_name = args.experiment_name or (
        f"Snapshot {args.variant} random-{seed}"
        if args.random_training
        else f"Snapshot {args.variant} seed-{seed}"
    )

    tracker = ExpTracker.init(
        project=args.project_name,
        experiment=experiment_name,
        team=args.team_name,
        init_params=InitParams(
            create_team_if_not_exists=True,
            create_project_if_not_exists=True,
            create_experiment_if_not_exists=True,
        ),
        verbose=True,
    )

    try:
        tracker.status(ExperimentStatus.RUNNING)
        tracker.tags("snapshot-example", args.variant)
        tracker.features(
            [
                {
                    "name": "snapshot-file-compare",
                    "children": [
                        {"name": f"variant-{args.variant}"},
                        {
                            "name": (
                                "random-training"
                                if args.random_training
                                else "deterministic"
                            )
                        },
                    ],
                }
            ]
        )

        run_config = build_run_config(args, rng)
        history, accuracy, loss = run_training(
            tracker,
            run_config,
            steps=args.steps,
            sleep_seconds=args.sleep,
            rng=rng,
        )
        workspace = Path(args.workspace)
        write_training_files(
            workspace,
            run_config,
            history,
            accuracy,
            loss,
            file_count=args.file_count,
        )
        snapshot = tracker.log_snapshot([workspace], root=workspace.absolute())
        tracker.add_metric("loss", loss, label="final")
        tracker.add_metric("accuracy", accuracy, label="final")
        tracker.progress(100)
        tracker.status(ExperimentStatus.COMPLETE)
        logger.info(
            "snapshot_logged snapshot_id=%s included=%s uploaded=%s existing=%s",
            snapshot.snapshot_id,
            snapshot.included,
            snapshot.uploaded,
            snapshot.existing,
        )
    finally:
        tracker.close()


if __name__ == "__main__":
    main()
