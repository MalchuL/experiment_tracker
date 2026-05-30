from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, TypeAlias

from experiment_tracker_sdk.utils.chart.numeric import (
    extract_scatter3d_vertices,
    finite_float_values,
    finite_pie_slices,
    finite_scatter_xy,
    require_equal_lengths,
    try_finite_float,
)
from experiment_tracker_sdk.utils.chart.payload import (
    chart_artifact_filename,
    encode_chart_payload,
    histogram_preview,
    sample_xy_evenly,
)
from experiment_tracker_sdk.utils.chart.tensor_values import (
    flatten_numeric_values,
    iter_vertex_rows,
    label_sequence_length,
    numeric_sequence_length,
    vertex_row_count,
)

# Accepts Python sequences and, when installed, numpy.ndarray / torch.Tensor.
ChartNumericInput: TypeAlias = Iterable[Any] | Sequence[Any] | Any
ChartLabelInput: TypeAlias = Iterable[Any] | Sequence[Any] | str
ChartVertexInput: TypeAlias = Iterable[Any] | Sequence[Any] | Any
ChartLayoutConfig: TypeAlias = Mapping[str, Any] | None

__all__ = [
    "ChartLabelInput",
    "ChartLayoutConfig",
    "ChartNumericInput",
    "ChartVertexInput",
    "chart_artifact_filename",
    "encode_chart_payload",
    "extract_scatter3d_vertices",
    "finite_float_values",
    "finite_pie_slices",
    "finite_scatter_xy",
    "flatten_numeric_values",
    "histogram_preview",
    "iter_vertex_rows",
    "label_sequence_length",
    "numeric_sequence_length",
    "require_equal_lengths",
    "sample_xy_evenly",
    "vertex_row_count",
    "try_finite_float",
]
