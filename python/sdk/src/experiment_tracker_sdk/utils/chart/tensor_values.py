from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from typing import Any


def _to_cpu_numpy(value: Any) -> Any:
    if hasattr(value, "detach") and callable(value.detach):
        value = value.detach()
    if hasattr(value, "cpu") and callable(value.cpu):
        value = value.cpu()
    if hasattr(value, "numpy") and callable(value.numpy):
        return value.numpy()
    return value


def _is_numpy_ndarray(value: Any) -> bool:
    return type(value).__name__ == "ndarray" and type(value).__module__ == "numpy"


def _is_torch_tensor(value: Any) -> bool:
    module = type(value).__module__
    return module.startswith("torch") and hasattr(value, "detach")


def _ndarray_ravel_list(value: Any) -> list[Any]:
    return value.ravel().tolist()


def _tensor_ravel_list(value: Any) -> list[Any]:
    flattened = value.reshape(-1)
    if hasattr(flattened, "tolist") and callable(flattened.tolist):
        return flattened.tolist()
    return list(flattened)


def numeric_sequence_length(values: Any) -> int:
    """Return element count for a 1D or flattenable numeric series.

    Args:
        values: Python sequence, numpy array, torch tensor, or similar.

    Returns:
        Number of scalar elements after flattening tensor-like inputs.
    """
    if isinstance(values, str | bytes):
        return len(values)
    if isinstance(values, Sequence) and not hasattr(values, "reshape"):
        return len(values)

    converted = _to_cpu_numpy(values)
    if _is_numpy_ndarray(converted):
        return int(converted.size)
    if _is_torch_tensor(values):
        return int(values.numel())
    if _is_numpy_ndarray(values):
        return int(values.size)
    if hasattr(values, "numel") and callable(values.numel):
        return int(values.numel())

    flattened = flatten_numeric_values(values)
    if isinstance(flattened, list):
        return len(flattened)
    return len(list(flattened))


def label_sequence_length(labels: Any) -> int:
    """Return the number of pie-chart labels.

    Args:
        labels: Sequence of label strings (not a single ``str``).

    Returns:
        Label count.

    Raises:
        ValueError: If ``labels`` is a single string.
    """
    if isinstance(labels, str):
        raise ValueError(
            "labels must be a sequence of label strings, not a single string"
        )
    if isinstance(labels, Sequence):
        return len(labels)
    return len(list(labels))


def vertex_row_count(vertices: Any) -> int:
    """Return the number of 3D points represented by a vertices input.

    Args:
        vertices: ``(N, 3)`` arrays, flat ``3N`` buffers, or sequences of triples.

    Returns:
        Point count ``N``.

    Raises:
        ValueError: If ``vertices`` is a string or bytes object.
    """
    if isinstance(vertices, str | bytes):
        raise ValueError("vertices must be a sequence of 3D points")

    converted = _to_cpu_numpy(vertices)
    source = converted if converted is not vertices else vertices

    if _is_numpy_ndarray(source) or _is_torch_tensor(source):
        array = source
        if hasattr(array, "numpy") and callable(array.numpy):
            array = array.numpy()
        ndim = getattr(array, "ndim", None)
        if ndim == 2 and array.shape[1] >= 3:
            return int(array.shape[0])
        if ndim == 1:
            if array.shape[0] == 3:
                return 1
            if array.shape[0] % 3 == 0:
                return int(array.shape[0] // 3)
        return int(array.size)

    if isinstance(vertices, Sequence):
        return len(vertices)

    return sum(1 for _ in iter_vertex_rows(vertices))


def flatten_numeric_values(values: Any) -> Iterable[Any]:
    """Flatten numpy/torch inputs to a 1D sequence for histograms and 1D series.

    Args:
        values: Python sequence, numpy array, torch tensor, or scalar container.

    Returns:
        Iterable of scalar elements (list for tensor inputs, unchanged for
        plain sequences).
    """
    if isinstance(values, str | bytes):
        return values
    if isinstance(values, Sequence) and not hasattr(values, "reshape"):
        return values

    converted = _to_cpu_numpy(values)
    if _is_numpy_ndarray(converted):
        return _ndarray_ravel_list(converted)
    if _is_torch_tensor(values):
        return _tensor_ravel_list(values)
    if _is_numpy_ndarray(values):
        return _ndarray_ravel_list(values)
    if hasattr(values, "ravel") and callable(values.ravel):
        raveled = values.ravel()
        if hasattr(raveled, "tolist") and callable(raveled.tolist):
            return raveled.tolist()
        return raveled
    if hasattr(values, "flatten") and callable(values.flatten):
        flattened = values.flatten()
        if hasattr(flattened, "tolist") and callable(flattened.tolist):
            return flattened.tolist()
        return flattened
    return values


def iter_vertex_rows(vertices: Any) -> Iterable[Any]:
    """Yield one 3D point per iteration from heterogeneous vertex storage.

    Args:
        vertices: ``(N, 3)`` tensor/array, flat ``3N`` buffer, or sequence of points.

    Returns:
        Iterable of per-vertex rows (each with at least three coordinates).
    """
    if isinstance(vertices, str | bytes):
        return (vertices,)

    converted = _to_cpu_numpy(vertices)
    source = converted if converted is not vertices else vertices

    if _is_numpy_ndarray(source) or _is_torch_tensor(source):
        return _iter_tensor_vertices(source)

    if _is_numpy_ndarray(vertices) or _is_torch_tensor(vertices):
        return _iter_tensor_vertices(vertices)

    return vertices


def _iter_tensor_vertices(array: Any) -> Iterator[Sequence[Any]]:
    if hasattr(array, "detach") and callable(array.detach):
        array = array.detach()
    if hasattr(array, "cpu") and callable(array.cpu):
        array = array.cpu()
    if hasattr(array, "numpy") and callable(array.numpy):
        array = array.numpy()

    ndim = getattr(array, "ndim", None)
    if ndim is None:
        yield array
        return

    if ndim == 1:
        if array.shape[0] == 3:
            yield array
            return
        if array.shape[0] % 3 == 0:
            reshaped = array.reshape(-1, 3)
            for row in reshaped:
                yield row
            return
        for item in array:
            yield item
        return

    if ndim == 2 and array.shape[1] >= 3:
        for row in array:
            yield row[:3]
        return

    flat = array.reshape(-1)
    if flat.shape[0] % 3 == 0 and flat.shape[0] >= 3:
        for row in flat.reshape(-1, 3):
            yield row
        return

    for item in flat:
        yield item
