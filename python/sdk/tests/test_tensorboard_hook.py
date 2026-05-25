from __future__ import annotations

import sys
from types import SimpleNamespace


class FakeArray:
    def __init__(self, shape: tuple[int, ...]) -> None:
        self.shape = shape
        self.ndim = len(shape)
        self.dtype = "uint8"

    def __getitem__(self, index):
        if index == 0:
            return FakeArray(self.shape[1:])
        if isinstance(index, tuple) and index == (
            slice(None),
            slice(None),
            0,
        ):
            return FakeArray(self.shape[:2])
        raise AssertionError(f"Unexpected index: {index}")


def _fake_numpy_module():
    def moveaxis(image, source, destination):
        assert source == 0
        assert destination == -1
        return FakeArray((image.shape[1], image.shape[2], image.shape[0]))

    return SimpleNamespace(ndarray=FakeArray, moveaxis=moveaxis)


def test_tensorboard_summary_writer_patch_captures_scalars_and_images(
    monkeypatch,
) -> None:
    from experiment_tracker_sdk.utils.hooks import tensorboard

    monkeypatch.setitem(sys.modules, "numpy", _fake_numpy_module())
    original_calls = []

    class FakeTracker:
        def __init__(self) -> None:
            self.scalars = []
            self.images = []

        def add_scalar(self, tag, scalar_value, global_step=0, walltime=0) -> None:
            self.scalars.append((tag, scalar_value, global_step, walltime))

        def add_image(self, tag, img_tensor, global_step=0, walltime=0) -> None:
            self.images.append((tag, img_tensor, global_step, walltime))

    class FakeSummaryWriter:
        def add_scalar(self, tag, scalar_value, global_step=None, walltime=None):
            original_calls.append(("scalar", tag, scalar_value, global_step, walltime))
            return "original-scalar"

        def add_image(
            self,
            tag,
            img_tensor,
            global_step=None,
            walltime=None,
            dataformats="CHW",
        ):
            original_calls.append(
                ("image", tag, img_tensor, global_step, walltime, dataformats)
            )
            return "original-image"

    tracker = FakeTracker()
    tensorboard._active_tracker = tracker
    tensorboard._patch_summary_writer(FakeSummaryWriter)

    writer = FakeSummaryWriter()

    assert writer.add_scalar("loss", 1.5, global_step=7, walltime=12.0) == (
        "original-scalar"
    )
    chw_image = FakeArray((3, 4, 5))
    assert (
        writer.add_image(
            "sample",
            chw_image,
            global_step=8,
            walltime=13.0,
            dataformats="CHW",
        )
        == "original-image"
    )
    assert tracker.scalars == [("loss", 1.5, 7, 12.0)]
    assert len(tracker.images) == 1
    assert tracker.images[0][0] == "sample"
    assert tracker.images[0][1].shape == (4, 5, 3)
    assert tracker.images[0][2:] == (8, 13.0)
    assert original_calls[0] == ("scalar", "loss", 1.5, 7, 12.0)
    assert original_calls[1] == ("image", "sample", chw_image, 8, 13.0, "CHW")

    tensorboard._active_tracker = None


def test_tensorboard_image_prepare_handles_single_channel_chw(monkeypatch) -> None:
    from experiment_tracker_sdk.utils.hooks.tensorboard import (
        _prepare_image_for_tracker,
    )

    monkeypatch.setitem(sys.modules, "numpy", _fake_numpy_module())
    image = FakeArray((1, 4, 5))

    prepared = _prepare_image_for_tracker(image, "CHW")

    assert prepared.shape == (4, 5)
