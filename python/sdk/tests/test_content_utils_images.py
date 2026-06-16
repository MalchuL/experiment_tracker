from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from experiment_tracker_sdk.error import ExpTrackerAPIError
from experiment_tracker_sdk.utils.content_utils import image_data_to_png_bytes


class _FakeTorchTensor:
    __module__ = "torch"

    def __init__(self, array: np.ndarray) -> None:
        self._array = array

    def detach(self) -> "_FakeTorchTensor":
        return self

    def cpu(self) -> "_FakeTorchTensor":
        return self

    def numpy(self) -> np.ndarray:
        return self._array


def _assert_png(payload: bytes) -> None:
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")


def test_image_data_to_png_bytes_accepts_chw_torch_tensor() -> None:
    chw = np.array(
        [
            [[0, 255], [255, 0]],
            [[255, 0], [0, 255]],
            [[0, 0], [255, 255]],
        ],
        dtype=np.uint8,
    )
    payload = image_data_to_png_bytes(_FakeTorchTensor(chw))
    _assert_png(payload)
    assert Image.open(__import__("io").BytesIO(payload)).size == (2, 2)


def test_image_data_to_png_bytes_accepts_hw_torch_tensor() -> None:
    hw = np.array([[0, 128], [64, 255]], dtype=np.uint8)
    payload = image_data_to_png_bytes(_FakeTorchTensor(hw))
    _assert_png(payload)


def test_image_data_to_png_bytes_reports_unsupported_type() -> None:
    with pytest.raises(ExpTrackerAPIError, match=r"Unsupported image type <class 'int'>") as exc:
        image_data_to_png_bytes(42)  # type: ignore[arg-type]

    assert "numpy.ndarray" in str(exc.value)
    assert "torch.Tensor" in str(exc.value)
