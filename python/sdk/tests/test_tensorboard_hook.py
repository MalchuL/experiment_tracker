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
            self.histograms = []
            self.scatters = []
            self.meshes = []
            self.hparams = []
            self._experiment = SimpleNamespace(
                features=[{"name": "model", "children": [{"name": "cnn"}]}]
            )

        def add_scalar(self, tag, scalar_value, global_step=0, walltime=0) -> None:
            self.scalars.append((tag, scalar_value, global_step, walltime))

        def add_image(self, tag, img_tensor, global_step=0, walltime=0) -> None:
            self.images.append((tag, img_tensor, global_step, walltime))

        def add_histogram(
            self, tag, values, global_step=0, bins=None, walltime=0
        ) -> None:
            self.histograms.append((tag, values, global_step, bins, walltime))

        def add_scatter(
            self, tag, x, y, global_step=0, mode="markers", walltime=0
        ) -> None:
            self.scatters.append((tag, x, y, global_step, mode, walltime))

        def add_mesh(
            self,
            tag,
            vertices,
            colors=None,
            faces=None,
            config_dict=None,
            global_step=0,
            walltime=0,
        ) -> None:
            self.meshes.append(
                (tag, vertices, colors, faces, config_dict, global_step, walltime)
            )

        def features(self, features) -> None:
            self._experiment.features = features

        def log_hparams(self, hparams) -> None:
            self.hparams.append(hparams)

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

        def add_hparams(self, hparam_dict, metric_dict=None, name=None):
            original_calls.append(("hparams", hparam_dict, metric_dict, name))
            return "original-hparams"

        def add_histogram(
            self,
            tag,
            values,
            global_step=None,
            bins="tensorflow",
            walltime=None,
            max_bins=None,
        ):
            original_calls.append(
                ("histogram", tag, values, global_step, bins, walltime, max_bins)
            )
            return "original-histogram"

        def add_scatter(
            self, tag, x, y, global_step=None, walltime=None, mode="markers"
        ):
            original_calls.append(
                ("scatter", tag, x, y, global_step, walltime, mode)
            )
            return "original-scatter"

        def add_mesh(
            self,
            tag,
            vertices,
            colors=None,
            faces=None,
            config_dict=None,
            global_step=None,
            walltime=None,
        ):
            original_calls.append(
                (
                    "mesh",
                    tag,
                    vertices,
                    colors,
                    faces,
                    config_dict,
                    global_step,
                    walltime,
                )
            )
            return "original-mesh"

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
    hparams = {"lr": 0.001, "batch_size": 128, "shuffle": True}
    assert (
        writer.add_hparams(hparams, {"val/accuracy": 0.9}, name="run-config")
        == "original-hparams"
    )
    hist_values = [0.0, 1.0, 2.0]
    assert (
        writer.add_histogram(
            "weights",
            hist_values,
            global_step=4,
            bins=8,
            walltime=5.0,
        )
        == "original-histogram"
    )
    assert (
        writer.add_scatter(
            "points",
            [0, 1],
            [2, 3],
            global_step=6,
            walltime=7.0,
            mode="lines",
        )
        == "original-scatter"
    )
    mesh_vertices = [(0, 1, 2), (3, 4, 5)]
    assert (
        writer.add_mesh(
            "cloud",
            mesh_vertices,
            colors=[1.0, 2.0],
            global_step=9,
            walltime=10.0,
        )
        == "original-mesh"
    )
    assert tracker.scalars == [("loss", 1.5, 7, 12.0)]
    assert len(tracker.images) == 1
    assert tracker.images[0][0] == "sample"
    assert tracker.images[0][1].shape == (4, 5, 3)
    assert tracker.images[0][2:] == (8, 13.0)
    assert tracker.hparams == [hparams]
    assert tracker._experiment.features == [
        {"name": "model", "children": [{"name": "cnn"}]}
    ]
    assert original_calls[0] == ("scalar", "loss", 1.5, 7, 12.0)
    assert original_calls[1] == ("image", "sample", chw_image, 8, 13.0, "CHW")
    assert original_calls[2] == (
        "hparams",
        hparams,
        {"val/accuracy": 0.9},
        "run-config",
    )
    assert tracker.histograms == [("weights", hist_values, 4, 8, 5.0)]
    assert tracker.scatters == [("points", [0, 1], [2, 3], 6, "lines", 7.0)]
    assert tracker.meshes[0][0] == "cloud"
    assert tracker.meshes[0][1] == mesh_vertices
    assert tracker.meshes[0][2] == [1.0, 2.0]
    assert tracker.meshes[0][5:] == (9, 10.0)
    assert original_calls[3] == (
        "histogram",
        "weights",
        hist_values,
        4,
        8,
        5.0,
        None,
    )
    assert original_calls[4] == ("scatter", "points", [0, 1], [2, 3], 6, 7.0, "lines")
    assert original_calls[5][0] == "mesh"
    assert original_calls[5][1] == "cloud"

    tensorboard._active_tracker = None


def test_tensorboard_histogram_bins_string_uses_tracker_default() -> None:
    from experiment_tracker_sdk.utils.hooks.tensorboard import (
        _histogram_bins_for_tracker,
    )

    assert _histogram_bins_for_tracker("tensorflow") is None
    assert _histogram_bins_for_tracker(16) == 16


def test_tensorboard_mesh_prepare_squeezes_batch_dimension() -> None:
    from experiment_tracker_sdk.utils.hooks.tensorboard import _prepare_mesh_for_tracker

    vertices = FakeArray((1, 2, 3))
    colors = FakeArray((1, 2, 3))
    prepared_vertices, prepared_colors = _prepare_mesh_for_tracker(vertices, colors)

    assert prepared_vertices.shape == (2, 3)
    assert prepared_colors.shape == (2, 3)


def test_monkey_patch_tensorboard_sets_tracker_and_patches_supported_modules(
    monkeypatch,
) -> None:
    from experiment_tracker_sdk.utils.hooks import tensorboard

    patched_modules = []
    tracker = object()

    monkeypatch.setattr(tensorboard.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(
        tensorboard,
        "_patch_summary_writer_module",
        lambda module_name: patched_modules.append(module_name),
    )

    tensorboard._active_tracker = None
    tensorboard.monkey_patch_tensorboard(tracker)

    assert tensorboard._active_tracker is tracker
    assert patched_modules == ["tensorboardX", "torch.utils.tensorboard"]

    tensorboard._active_tracker = None


def test_tensorboard_scalar_values_are_converted_to_float() -> None:
    from experiment_tracker_sdk.utils.hooks.tensorboard import _scalar_to_float

    class FakeTorchScalar:
        def __init__(self) -> None:
            self.detached = False
            self.moved_to_cpu = False

        def detach(self):
            self.detached = True
            return self

        def cpu(self):
            self.moved_to_cpu = True
            return self

        def item(self):
            return "1.25"

    class FakeNumpyScalar:
        def item(self):
            return 2.5

    torch_scalar = FakeTorchScalar()

    assert _scalar_to_float(torch_scalar) == 1.25
    assert torch_scalar.detached is True
    assert torch_scalar.moved_to_cpu is True
    assert _scalar_to_float(FakeNumpyScalar()) == 2.5
    assert _scalar_to_float(3) == 3.0


def test_tensorboard_summary_writer_patch_converts_scalar_for_tracker() -> None:
    from experiment_tracker_sdk.utils.hooks import tensorboard

    original_calls = []

    class FakeScalar:
        def item(self):
            return "4.5"

    class FakeTracker:
        def __init__(self) -> None:
            self.scalars = []

        def add_scalar(self, tag, scalar_value, global_step=0, walltime=0) -> None:
            self.scalars.append((tag, scalar_value, global_step, walltime))

    class FakeSummaryWriter:
        def add_scalar(self, tag, scalar_value, global_step=None, walltime=None):
            original_calls.append(("scalar", tag, scalar_value, global_step, walltime))
            return "original-scalar"

    tracker = FakeTracker()
    scalar = FakeScalar()
    tensorboard._active_tracker = tracker
    tensorboard._patch_summary_writer(FakeSummaryWriter)

    writer = FakeSummaryWriter()

    assert writer.add_scalar("loss", scalar, global_step=7) == "original-scalar"
    assert tracker.scalars == [("loss", 4.5, 7, 0)]
    assert original_calls == [("scalar", "loss", scalar, 7, None)]

    tensorboard._active_tracker = None


def test_tensorboard_image_prepare_handles_single_channel_chw(monkeypatch) -> None:
    from experiment_tracker_sdk.utils.hooks.tensorboard import (
        _prepare_image_for_tracker,
    )

    monkeypatch.setitem(sys.modules, "numpy", _fake_numpy_module())
    image = FakeArray((1, 4, 5))

    prepared = _prepare_image_for_tracker(image, "CHW")

    assert prepared.shape == (4, 5)
