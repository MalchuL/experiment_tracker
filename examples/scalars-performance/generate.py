"""Deterministic scalar workload: dump offline, optionally log live using the local SDK.

Offline: uv run --no-project python examples/scalars-performance/generate.py --dump /tmp/scalars.json
Live: uv run --project python/sdk examples/scalars-performance/generate.py --upload --seconds 60
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


def scalar_values(experiment: int, step: int, metrics: int) -> dict[str, float]:
    return {
        f"train/metric{metric:03d}": round(math.sin(step / 30 + metric) + experiment / 10, 6)
        for metric in range(metrics)
        if metric % 5 != 0 or step % 7 == 0
    }


def build_dump(experiments: int, metrics: int, steps: int) -> dict:
    data = []
    for experiment in range(experiments):
        series = {f"train/metric{metric:03d}": {"x": [], "y": []} for metric in range(metrics)}
        for step in range(steps):
            for name, value in scalar_values(experiment, step, metrics).items():
                series[name]["x"].append(step)
                series[name]["y"].append(value)
        data.append({"experiment_id": str(uuid5(NAMESPACE_URL, f"scalar-performance-{experiment}")), "scalars": series})
    return {"data": data, "hasNext": False, "size": len(data), "total": len(data)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", type=Path)
    parser.add_argument("--experiments", type=int, default=8)
    parser.add_argument("--metrics", type=int, default=72)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--project", default="Scalar performance")
    parser.add_argument("--run", default="performance")
    parser.add_argument("--seconds", type=float, default=60)
    args = parser.parse_args()
    if min(args.experiments, args.metrics, args.steps) < 1 or args.seconds < 0:
        parser.error("Counts must be positive; seconds must be nonnegative")
    if not args.dump and not args.upload:
        parser.error("Choose --dump, --upload, or both")
    if args.dump:
        args.dump.write_text(json.dumps(build_dump(args.experiments, args.metrics, args.steps), separators=(",", ":")))
        print(f"Dumped {args.experiments} experiments × {args.metrics} scalars × {args.steps} steps to {args.dump}")
    if args.upload:
        from experiment_tracker_sdk import ExpTracker, ExperimentStatus, InitParams

        trackers = []
        try:
            for index in range(args.experiments):
                tracker = ExpTracker.init(project=args.project, experiment=f"{args.run}-{index}", init_params=InitParams(
                    create_project_if_not_exists=True, create_experiment_if_not_exists=True,
                ))
                trackers.append(tracker)
                tracker.status(ExperimentStatus.RUNNING)
            started = time.monotonic()
            for step in range(args.steps):
                for index, tracker in enumerate(trackers):
                    tracker.add_scalars("", scalar_values(index, step, args.metrics), global_step=step)
                if step % 25 == 0:
                    for tracker in trackers:
                        tracker.flush()
                time.sleep(max(0, started + args.seconds * (step + 1) / args.steps - time.monotonic()))
            for tracker in trackers:
                tracker.flush()
                tracker.status(ExperimentStatus.COMPLETE)
        except BaseException:
            for tracker in trackers:
                tracker.status(ExperimentStatus.FAILED)
            raise
        finally:
            for tracker in trackers:
                tracker.close()


if __name__ == "__main__":
    main()
