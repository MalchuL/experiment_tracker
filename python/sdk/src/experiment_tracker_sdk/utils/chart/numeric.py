from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any

from experiment_tracker_sdk.utils.chart.tensor_values import (
    flatten_numeric_values,
    iter_vertex_rows,
    label_sequence_length,
    numeric_sequence_length,
    vertex_row_count,
)


def require_equal_lengths(
    left: Any,
    right: Any,
    *,
    left_name: str,
    right_name: str,
    left_length=numeric_sequence_length,
    right_length=numeric_sequence_length,
) -> None:
    """Validate that two inputs have the same element count before pairing.

    Args:
        left: First series (e.g. scatter ``x`` or pie ``labels``).
        right: Second series (e.g. scatter ``y`` or pie ``values``).
        left_name: Name used in error messages for ``left``.
        right_name: Name used in error messages for ``right``.
        left_length: Callable that returns the length of ``left``.
        right_length: Callable that returns the length of ``right``.

    Raises:
        ValueError: If the computed lengths differ.
    """
    left_len = left_length(left)
    right_len = right_length(right)
    if left_len != right_len:
        raise ValueError(
            f"{left_name} and {right_name} must have the same length "
            f"(got {left_len} and {right_len})"
        )


def try_finite_float(value) -> float | None:
    """Convert a scalar-like value to a finite float, or return None.

    Args:
        value: Python number, or tensor/numpy scalar with ``.item()``.

    Returns:
        Finite float, or ``None`` if conversion fails or the value is non-finite.
    """
    try:
        item: Any = (
            value.item()
            if hasattr(value, "item") and callable(value.item)
            else value
        )
        number = float(item)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def finite_float_values(values: Iterable | Any) -> list[float]:
    """Flatten and keep only finite floats from a numeric series.

    Args:
        values: Sequence, numpy array, or torch tensor of numbers.

    Returns:
        1D list of finite floats suitable for histogram traces.
    """
    out: list[float] = []
    for value in flatten_numeric_values(values):
        number = try_finite_float(value)
        if number is not None:
            out.append(number)
    return out


def finite_scatter_xy(x: Any, y: Any) -> tuple[list[float], list[float]]:
    """Pair and filter scatter coordinates, dropping non-finite points.

    Args:
        x: X coordinates (sequence, numpy array, or torch tensor).
        y: Y coordinates (same constraints as ``x``).

    Returns:
        Aligned finite ``(x, y)`` lists.

    Raises:
        ValueError: If flattened ``x`` and ``y`` have different lengths.
    """
    require_equal_lengths(x, y, left_name="x", right_name="y")
    x_values: list[float] = []
    y_values: list[float] = []
    for x_item, y_item in zip(flatten_numeric_values(x), flatten_numeric_values(y)):
        x_number = try_finite_float(x_item)
        y_number = try_finite_float(y_item)
        if x_number is not None and y_number is not None:
            x_values.append(x_number)
            y_values.append(y_number)
    return x_values, y_values


def finite_pie_slices(labels: Any, values: Any) -> tuple[list[str], list[float]]:
    """Pair pie labels with finite slice values, dropping invalid entries.

    Args:
        labels: Slice labels (sequence of strings; not a single ``str``).
        values: Slice sizes (sequence, numpy array, or torch tensor).

    Returns:
        Aligned ``(labels, values)`` lists with only finite numeric values.

    Raises:
        ValueError: If ``labels`` and ``values`` have different lengths, or
            ``labels`` is a bare string.
    """
    require_equal_lengths(
        labels,
        values,
        left_name="labels",
        right_name="values",
        left_length=label_sequence_length,
        right_length=numeric_sequence_length,
    )
    labels_list: list[str] = []
    numeric_values: list[float] = []
    for label, value in zip(labels, flatten_numeric_values(values)):
        number = try_finite_float(value)
        if number is not None:
            labels_list.append(str(label))
            numeric_values.append(number)
    return labels_list, numeric_values


def extract_scatter3d_vertices(
    vertices: Iterable | Any,
) -> tuple[list[float], list[float], list[float]]:
    """Extract finite x/y/z coordinates from 3D point inputs.

    Args:
        vertices: Point rows ``(x, y, z)``, ``(N, 3)`` arrays, or flat ``3N`` buffers.

    Returns:
        Three parallel lists of finite coordinates for a 3D scatter trace.
    """
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for point in iter_vertex_rows(vertices):
        coords = _vertex_xyz(point)
        if coords is not None:
            xs.append(coords[0])
            ys.append(coords[1])
            zs.append(coords[2])
    return xs, ys, zs


def _vertex_xyz(point: Any) -> tuple[float, float, float] | None:
    is_ndarray = (
        type(point).__name__ == "ndarray" and type(point).__module__ == "numpy"
    )
    if is_ndarray:
        if point.size < 3:
            return None
        try:
            x, y, z = float(point[0]), float(point[1]), float(point[2])
        except (TypeError, ValueError):
            return None
    elif isinstance(point, Sequence) and not isinstance(point, str | bytes):
        if len(point) < 3:
            return None
        try:
            x, y, z = float(point[0]), float(point[1]), float(point[2])
        except (TypeError, ValueError):
            return None
    else:
        return None
    if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
        return x, y, z
    return None
