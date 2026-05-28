from __future__ import annotations

import json
import re


def chart_artifact_filename(tag: str, global_step: int) -> str:
    """Build a safe step artifact filename for chart JSON uploads.

    Args:
        tag: Logical series name from the training API.
        global_step: Training step the artifact is logged at.

    Returns:
        Filename of the form ``{safe_tag}_{global_step}.chart.json``.
    """
    safe_tag = re.sub(r"[^A-Za-z0-9._-]+", "_", tag).strip("._-") or "artifact"
    return f"{safe_tag}_{global_step}.chart.json"


def encode_chart_payload(
    data: list[dict],
    layout: dict | None = None,
    config: dict | None = None,
) -> bytes:
    """Serialize chart traces and layout to UTF-8 JSON bytes for upload.

    Args:
        data: Trace dictionaries (type, coordinates, styling) consumed by the UI.
        layout: Optional layout object (title, axes, margins).
        config: Optional viewer config; defaults to responsive layout when omitted.

    Returns:
        Compact JSON bytes with ``schemaVersion`` set to 1.
    """
    payload = {
        "schemaVersion": 1,
        "data": data,
        "layout": layout or {},
        "config": config or {"responsive": True},
    }
    return json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8")


def sample_xy_evenly(
    x_values: list[float], y_values: list[float], max_points: int
) -> tuple[list[float], list[float]]:
    """Downsample aligned x/y series to at most ``max_points`` evenly spaced pairs.

    Args:
        x_values: Full x coordinates (same length as ``y_values``).
        y_values: Full y coordinates.
        max_points: Maximum number of points to keep for metadata previews.

    Returns:
        Subsampled ``(x, y)`` lists preserving endpoints when downsampling.
    """
    total = min(len(x_values), len(y_values))
    if total <= max_points:
        return x_values[:total], y_values[:total]
    if max_points <= 1:
        return [x_values[0]], [y_values[0]]
    last_index = total - 1
    indexes = [
        round(i * last_index / (max_points - 1)) for i in range(max_points)
    ]
    return [x_values[i] for i in indexes], [y_values[i] for i in indexes]


def histogram_preview(values: list[float], bins: int) -> dict:
    """Compute bin edges and counts for scatter-card metadata previews.

    Args:
        values: Finite numeric samples already normalized to floats.
        bins: Target number of histogram bins.

    Returns:
        Dict with ``bins`` (edge list), ``counts``, and ``total`` sample count.
    """
    if not values:
        return {"bins": [], "counts": [], "total": 0}
    lo = min(values)
    hi = max(values)
    if lo == hi:
        return {"bins": [lo, hi], "counts": [len(values)], "total": len(values)}
    bin_count = max(1, bins)
    width = (hi - lo) / bin_count
    counts = [0 for _ in range(bin_count)]
    for value in values:
        idx = min(int((value - lo) / width), bin_count - 1)
        counts[idx] += 1
    edges = [lo + width * i for i in range(bin_count + 1)]
    return {"bins": edges, "counts": counts, "total": len(values)}
