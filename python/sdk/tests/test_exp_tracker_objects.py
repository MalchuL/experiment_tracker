import json
from io import BytesIO, StringIO
from pathlib import Path
from uuid import UUID

import numpy as np
import pytest
from PIL import Image, features

from experiment_tracker_sdk.exp_tracker import ExpTracker


class _FakeExperimentArtifactsService:
    def upload_and_log_experiment_artifact_at_step(
        self,
        experiment_id: str,
        file,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict | None = None,
        tags: list | None = None,
    ):
        return {
            "kind": "upload_at_step",
            "experiment_id": experiment_id,
            "file": file,
            "name": name,
            "artifact_type": artifact_type,
            "step": step,
            "metadata": metadata,
            "tags": tags,
        }

    def upsert_named_experiment_artifact(
        self,
        experiment_id: str,
        filepath: str,
        file,
        name: str | None = None,
    ):
        return {
            "kind": "upsert_named",
            "experiment_id": experiment_id,
            "filepath": filepath,
            "file": file,
            "name": name,
        }


class _FakeRegistry:
    def __init__(self):
        self.experiment_artifacts = _FakeExperimentArtifactsService()


class _FakeClient:
    def __init__(self):
        self.uploaded: list[tuple[str, bytes, str, str, dict]] = []
        self.uploaded_specs: list[dict] = []
        self.final_uploaded: list[tuple[str, str, str, bytes, str]] = []
        self.request_verbose: list[bool] = []

    def request(self, request_spec, *, options=None, **_kwargs):
        verbose = options.verbose if options is not None else False
        self.request_verbose.append(verbose)
        if request_spec["kind"] == "upload_at_step":
            file = request_spec["file"]
            self.uploaded_specs.append(request_spec)
            self.uploaded.append(
                (
                    file.filename,
                    file.content,
                    file.content_type,
                    request_spec["name"],
                    request_spec["metadata"] or {},
                )
            )
            return {"status": "logged"}
        if request_spec["kind"] == "upsert_named":
            file = request_spec["file"]
            self.final_uploaded.append(
                (
                    request_spec["name"],
                    request_spec["filepath"],
                    file.filename,
                    file.content,
                    file.content_type,
                )
            )
            return {"status": "upserted"}
        raise AssertionError(f"Unexpected request: {request_spec}")

    def queued_request(self, request_spec):
        raise AssertionError(f"Unexpected queued request: {request_spec}")

    def flush(self):
        pass

    def close(self):
        pass


def _create_tracker(*, verbose: bool = False) -> tuple[ExpTracker, _FakeClient]:
    client = _FakeClient()
    tracker = ExpTracker(
        "exp-id",
        "proj-id",
        _FakeRegistry(),  # type: ignore[arg-type]
        client,  # type: ignore[arg-type]
        verbose=verbose,
    )
    return tracker, client


def test_exp_tracker_verbose_passes_flag_on_upload() -> None:
    tracker, client = _create_tracker(verbose=True)

    tracker.add_text("summary", "hello", global_step=1)

    assert client.request_verbose == [True]
    assert len(client.uploaded) == 1


def test_exp_tracker_per_call_verbose_overrides_tracker_default() -> None:
    tracker, client = _create_tracker(verbose=False)

    tracker.add_text("summary", "hello", global_step=1, verbose=True)

    assert client.request_verbose == [True]


def test_exp_tracker_per_call_verbose_false_overrides_tracker_true() -> None:
    tracker, client = _create_tracker(verbose=True)

    tracker.log_final_artifact("cfg", "yaml: true\n", verbose=False)

    assert client.request_verbose == [False]


def _checkerboard_array(
    size: int = 16,
    tile_size: int = 4,
    color_a: tuple[int, int, int] = (20, 40, 60),
    color_b: tuple[int, int, int] = (220, 180, 80),
) -> np.ndarray:
    rows, cols = np.indices((size, size))
    mask = ((rows // tile_size) + (cols // tile_size)) % 2 == 0
    image = np.empty((size, size, 3), dtype=np.uint8)
    image[mask] = color_a
    image[~mask] = color_b
    return image


def _int_gradient_array(size: int = 16) -> np.ndarray:
    x = np.linspace(-128, 383, size, dtype=np.int16)
    y = np.linspace(383, -128, size, dtype=np.int16)
    red = np.tile(x, (size, 1))
    green = np.tile(y[:, None], (1, size))
    blue = np.full((size, size), 127, dtype=np.int16)
    return np.stack([red, green, blue], axis=2)


def _float_heatmap_array(size: int = 16) -> np.ndarray:
    rows, cols = np.indices((size, size), dtype=np.float32)
    red = rows / max(size - 1, 1)
    green = cols / max(size - 1, 1)
    blue = (rows + cols) / max(2 * (size - 1), 1)
    return np.stack([red, green, blue], axis=2)


def _png_signature(content: bytes) -> bytes:
    return content[:8]


def _assert_png_upload(content: bytes) -> None:
    assert _png_signature(content) == b"\x89PNG\r\n\x1a\n"


def _image_bytes(image: Image.Image, image_format: str) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def _write_image(path: Path, image_format: str) -> bytes:
    content = _image_bytes(Image.fromarray(_checkerboard_array()), image_format)
    path.write_bytes(content)
    return content


def test_add_text_uploads_and_queues_object() -> None:
    tracker, client = _create_tracker()

    tracker.add_text("summary", "hello world", global_step=7)

    assert len(client.uploaded) == 1
    filename, content, content_type, name, metadata = client.uploaded[0]
    assert filename.startswith("summary_7")
    assert content == b"hello world"
    assert content_type == "text/plain"
    assert name == "summary"


def test_add_text_uploads_step_artifact_with_expected_filename() -> None:
    tracker, client = _create_tracker()

    tracker.add_text("text_from_str", "step note", global_step=400)

    assert len(client.uploaded) == 1
    filename, content, content_type, name, metadata = client.uploaded[0]
    assert filename == "text_from_str_400.txt"
    assert content == b"step note"
    assert content_type == "text/plain"
    assert name == "text_from_str"
    assert metadata == {"encoding": "utf-8"}


def test_add_image_uploads_pil_and_numpy_inputs_as_png() -> None:
    tracker, client = _create_tracker()
    images = {
        "image_from_PIL": Image.fromarray(_checkerboard_array()),
        "image_from_nparray_int": _int_gradient_array(),
        "image_from_nparray_uint": _checkerboard_array(
            color_a=(0, 80, 160),
            color_b=(255, 200, 40),
        ),
        "image_from_nparray_float": _float_heatmap_array(),
    }

    for tag, image in images.items():
        tracker.add_image(tag, image, global_step=500)

    assert len(client.uploaded) == len(images)
    for filename, content, content_type, name, metadata in client.uploaded:
        assert name in images
        assert filename == f"{name}_500.png"
        assert content_type == "image/png"
        assert metadata == {"format": "png"}
        _assert_png_upload(content)


class _FakeTorchTensor:
    __module__ = "torch"

    def __init__(self, values: list[float]) -> None:
        self._values = values

    def detach(self) -> "_FakeTorchTensor":
        return self

    def cpu(self) -> "_FakeTorchTensor":
        return self

    def reshape(self, _size: int) -> "_FakeTorchTensor":
        return self

    def tolist(self) -> list[float]:
        return list(self._values)


def test_add_histogram_flattens_numpy_2d_array() -> None:
    tracker, client = _create_tracker()

    tracker.add_histogram(
        "weights",
        np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float64),
        global_step=1,
        bins=2,
    )

    payload = json.loads(client.uploaded[0][1].decode("utf-8"))
    assert payload["data"][0]["x"] == [0.0, 1.0, 2.0, 3.0]


def test_add_histogram_accepts_torch_like_tensor() -> None:
    tracker, client = _create_tracker()

    tracker.add_histogram(
        "weights",
        _FakeTorchTensor([0.0, 1.0, 2.0]),
        global_step=2,
        bins=2,
    )

    payload = json.loads(client.uploaded[0][1].decode("utf-8"))
    assert payload["data"][0]["x"] == [0.0, 1.0, 2.0]


def test_add_scatter_accepts_numpy_1d_arrays() -> None:
    tracker, client = _create_tracker()

    tracker.add_scatter(
        "points",
        np.array([0.0, 1.0, 2.0]),
        np.array([10.0, 11.0, 12.0]),
        global_step=1,
    )

    trace = json.loads(client.uploaded[0][1].decode("utf-8"))["data"][0]
    assert trace["x"] == [0.0, 1.0, 2.0]
    assert trace["y"] == [10.0, 11.0, 12.0]


def test_add_mesh_accepts_numpy_vertex_rows() -> None:
    tracker, client = _create_tracker()

    tracker.add_mesh(
        "cloud",
        np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]),
        global_step=3,
    )

    trace = json.loads(client.uploaded[0][1].decode("utf-8"))["data"][0]
    assert trace["x"] == [0.0, 3.0]
    assert trace["y"] == [1.0, 4.0]
    assert trace["z"] == [2.0, 5.0]


def test_add_histogram_uploads_chart_json_with_metadata_preview() -> None:
    tracker, client = _create_tracker()

    tracker.add_histogram("weights", [0, 1, 2, 3], global_step=9, bins=2)

    assert len(client.uploaded) == 1
    filename, content, content_type, name, metadata = client.uploaded[0]
    assert filename == "weights_9.chart.json"
    assert content_type == "application/json"
    assert name == "weights"
    assert client.uploaded_specs[0]["artifact_type"] == "histogram"
    payload = json.loads(content.decode("utf-8"))
    assert payload["schemaVersion"] == 1
    assert payload["data"][0]["type"] == "histogram"
    assert payload["data"][0]["x"] == [0.0, 1.0, 2.0, 3.0]
    assert payload["data"][0]["nbinsx"] == 2
    assert metadata["preview_kind"] == "histogram_bins"
    preview = json.loads(metadata["preview_data"])
    assert preview["counts"] == [2, 2]
    assert preview["total"] == 4


def test_add_scatter_uploads_chart_json_with_env_limited_preview(monkeypatch) -> None:
    from experiment_tracker_sdk.settings import get_exp_tracker_settings

    get_exp_tracker_settings.cache_clear()
    monkeypatch.setenv("EXP_TRACKER_SCATTER_METADATA_MAX_POINTS", "3")
    tracker, client = _create_tracker()

    tracker.add_scatter("points", [0, 1, 2, 3, 4], [10, 11, 12, 13, 14], global_step=3)

    assert len(client.uploaded) == 1
    filename, content, content_type, name, metadata = client.uploaded[0]
    assert filename == "points_3.chart.json"
    assert content_type == "application/json"
    assert name == "points"
    assert client.uploaded_specs[0]["artifact_type"] == "scatter"
    payload = json.loads(content.decode("utf-8"))
    assert payload["data"][0]["type"] == "scatter"
    assert payload["data"][0]["x"] == [0.0, 1.0, 2.0, 3.0, 4.0]
    preview = json.loads(metadata["preview_data"])
    assert preview == {
        "x": [0.0, 2.0, 4.0],
        "y": [10.0, 12.0, 14.0],
        "total": 5,
        "sampled": 3,
    }
    get_exp_tracker_settings.cache_clear()


def test_add_scatter_raises_when_x_and_y_lengths_differ() -> None:
    tracker, _client = _create_tracker()

    with pytest.raises(ValueError, match="x and y must have the same length"):
        tracker.add_scatter("points", [0, 1, 2], [10, 11], global_step=1)


def test_add_pie_raises_when_labels_and_values_lengths_differ() -> None:
    tracker, _client = _create_tracker()

    with pytest.raises(ValueError, match="labels and values must have the same length"):
        tracker.add_pie("classes", ["a", "b"], [1, 2, 3], global_step=1)


def test_add_mesh_raises_when_colors_length_differs_from_vertices() -> None:
    tracker, _client = _create_tracker()

    with pytest.raises(ValueError, match="vertices and colors must have the same length"):
        tracker.add_mesh(
            "cloud",
            [(0, 1, 2), (3, 4, 5)],
            colors=[1.0, 2.0, 3.0],
            global_step=1,
        )


def test_add_scatter_skips_non_finite_pairs_without_misaligning() -> None:
    tracker, client = _create_tracker()

    tracker.add_scatter(
        "points",
        [0, float("nan"), 2, 3],
        [10, 20, 30, 40],
        global_step=1,
    )

    payload = json.loads(client.uploaded[0][1].decode("utf-8"))
    trace = payload["data"][0]
    assert trace["x"] == [0.0, 2.0, 3.0]
    assert trace["y"] == [10.0, 30.0, 40.0]


def test_add_pie_skips_non_finite_values_without_misaligning_labels() -> None:
    tracker, client = _create_tracker()

    tracker.add_pie("classes", ["a", "b", "c"], [1, float("nan"), 3], global_step=1)

    payload = json.loads(client.uploaded[0][1].decode("utf-8"))
    trace = payload["data"][0]
    assert trace["labels"] == ["a", "c"]
    assert trace["values"] == [1.0, 3.0]
    assert client.uploaded[0][4]["total_slices"] == "2"


def test_add_pie_uploads_chart_json() -> None:
    tracker, client = _create_tracker()

    tracker.add_pie("classes", ["cat", "dog"], [4, 6], global_step=2)

    assert len(client.uploaded) == 1
    filename, content, content_type, name, metadata = client.uploaded[0]
    assert filename == "classes_2.chart.json"
    assert content_type == "application/json"
    assert name == "classes"
    assert client.uploaded_specs[0]["artifact_type"] == "pie"
    payload = json.loads(content.decode("utf-8"))
    assert payload["data"][0]["type"] == "pie"
    assert payload["data"][0]["labels"] == ["cat", "dog"]
    assert payload["data"][0]["values"] == [4.0, 6.0]
    assert metadata["total_slices"] == "2"


def test_add_mesh_uploads_point_cloud_chart_json() -> None:
    tracker, client = _create_tracker()

    tracker.add_mesh("cloud", [(0, 1, 2), (3, 4, 5)], global_step=4)

    assert len(client.uploaded) == 1
    filename, content, content_type, name, metadata = client.uploaded[0]
    assert filename == "cloud_4.chart.json"
    assert content_type == "application/json"
    assert name == "cloud"
    assert client.uploaded_specs[0]["artifact_type"] == "point_cloud_3d"
    payload = json.loads(content.decode("utf-8"))
    trace = payload["data"][0]
    assert trace["type"] == "scatter3d"
    assert trace["x"] == [0.0, 3.0]
    assert trace["y"] == [1.0, 4.0]
    assert trace["z"] == [2.0, 5.0]
    assert metadata["total_points"] == "2"


def test_log_final_artifact_uploads_without_step_suffix() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_artifact(
        "config",
        "learning_rate: 0.01",
        default_extension=".yaml",
    )

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "config"
    assert filepath == "final/config.yaml"
    assert filename == "config.yaml"
    assert content == b"learning_rate: 0.01"
    assert content_type == "text/plain"


def test_log_final_artifact_uploads_raw_bytes_with_defaults() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_artifact(
        "weights",
        b"binary-weights",
        default_content_type="application/octet-stream",
        default_extension=".bin",
    )

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "weights"
    assert filepath == "final/weights.bin"
    assert filename == "weights.bin"
    assert content == b"binary-weights"
    assert content_type == "application/octet-stream"


def test_log_final_artifact_sanitizes_default_filename_from_tag() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_artifact(
        "reports/final:summary?bad\x00chars",
        b"payload",
        default_content_type="application/octet-stream",
        default_extension=".bin",
    )

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "reports/final:summary?bad\x00chars"
    assert filepath == "final/reports_final_summary_bad_chars.bin"
    assert filename == "reports_final_summary_bad_chars.bin"
    assert content == b"payload"
    assert content_type == "application/octet-stream"


def test_log_final_text_sanitizes_default_filename_from_tag() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_text("final notes/v1:best?", "finished")

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "final notes/v1:best?"
    assert filepath == "final/final_notes_v1_best.txt"
    assert filename == "final_notes_v1_best.txt"
    assert content == b"finished"
    assert content_type == "text/plain"


def test_log_final_text_appends_default_extension_when_tag_looks_like_filename() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_text("notes.md", "finished")

    assert len(client.final_uploaded) == 1
    _, filepath, filename, _, _ = client.final_uploaded[0]
    assert filepath == "final/notes.md.txt"
    assert filename == "notes.md.txt"


def test_log_final_artifact_uses_uuid_filename_when_tag_has_no_safe_chars(
    monkeypatch,
) -> None:
    tracker, client = _create_tracker()
    monkeypatch.setattr(
        "experiment_tracker_sdk.utils.content_utils.uuid4",
        lambda: UUID("12345678-1234-5678-1234-567812345678"),
    )

    tracker.log_final_artifact(
        "///???",
        b"payload",
        default_content_type="application/octet-stream",
        default_extension=".bin",
    )

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "///???"
    assert filepath == "final/12345678123456781234567812345678.bin"
    assert filename == "12345678123456781234567812345678.bin"
    assert content == b"payload"
    assert content_type == "application/octet-stream"


def test_log_final_artifact_uploads_file_like_values() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_artifact(
        "bytes_buffer",
        BytesIO(b"buffer-bytes"),
        default_content_type="application/octet-stream",
        default_extension=".bin",
    )
    tracker.log_final_artifact(
        "text_buffer",
        StringIO("buffer text"),
        default_content_type="text/plain",
        default_extension=".txt",
    )

    assert len(client.final_uploaded) == 2
    assert client.final_uploaded[0] == (
        "bytes_buffer",
        "final/bytes_buffer.bin",
        "bytes_buffer.bin",
        b"buffer-bytes",
        "application/octet-stream",
    )
    assert client.final_uploaded[1] == (
        "text_buffer",
        "final/text_buffer.txt",
        "text_buffer.txt",
        b"buffer text",
        "text/plain",
    )


def test_log_final_artifact_uploads_existing_text_path(
    tmp_path: Path, monkeypatch
) -> None:
    tracker, client = _create_tracker()
    path = tmp_path / "notes.txt"
    path.write_text("from file", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    tracker.log_final_artifact("notes", "notes.txt")

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "notes"
    assert filepath == "notes.txt"
    assert filename == "notes.txt"
    assert content == b"from file"
    assert content_type == "text/plain"


def test_log_final_artifact_long_json_string_not_treated_as_path() -> None:
    """Regression: huge str payloads must not be passed to Path(...).exists()."""
    tracker, client = _create_tracker()

    payload = '{"k": "%s"}' % ("x" * 5000)
    tracker.log_final_artifact(
        "training_summary_json",
        payload,
        stored_filepath="final/summary.json",
        default_content_type="application/json",
        default_extension=".json",
    )

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "training_summary_json"
    assert filepath == "final/summary.json"
    assert content == payload.encode("utf-8")
    assert content_type == "application/json"


def test_log_final_image_uploads_png_bytes() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_image("preview", b"png-bytes")

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "preview"
    assert filepath == "final/preview.png"
    assert filename == "preview.png"
    assert content == b"png-bytes"
    assert content_type == "image/png"


def test_log_final_image_converts_pil_and_numpy_inputs_with_default_paths() -> None:
    tracker, client = _create_tracker()
    images = {
        "image_from_PIL": Image.fromarray(_checkerboard_array()),
        "image_from_nparray_int": _int_gradient_array(),
        "image_from_nparray_uint": _checkerboard_array(
            color_a=(10, 140, 210),
            color_b=(240, 230, 30),
        ),
        "image_from_nparray_float": _float_heatmap_array(),
    }

    for tag, image in images.items():
        tracker.log_final_image(tag, image)

    assert len(client.final_uploaded) == len(images)
    for name, filepath, filename, content, content_type in client.final_uploaded:
        assert name in images
        assert filepath == f"final/{name}.png"
        assert filename == f"{name}.png"
        assert content_type == "image/png"
        _assert_png_upload(content)


def test_log_final_image_preserves_jpeg_file(
    tmp_path: Path, monkeypatch
) -> None:
    tracker, client = _create_tracker()
    path = tmp_path / "image_from_jpeg.jpg"
    expected = _write_image(path, "JPEG")
    monkeypatch.chdir(tmp_path)

    tracker.log_final_image("image_from_jpeg", "image_from_jpeg.jpg")

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "image_from_jpeg"
    assert filepath == "image_from_jpeg.jpg"
    assert filename == "image_from_jpeg.jpg"
    assert content == expected
    assert content_type == "image/jpeg"


def test_log_final_artifact_preserves_jpeg_file(
    tmp_path: Path, monkeypatch
) -> None:
    tracker, client = _create_tracker()
    path = tmp_path / "artifact_image_from_jpeg.jpg"
    expected = _write_image(path, "JPEG")
    monkeypatch.chdir(tmp_path)

    tracker.log_final_artifact("artifact_image_from_jpeg", path)

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "artifact_image_from_jpeg"
    assert filepath == "artifact_image_from_jpeg.jpg"
    assert filename == "artifact_image_from_jpeg.jpg"
    assert content == expected
    assert content_type == "image/jpeg"


@pytest.mark.skipif(
    not features.check("webp"),
    reason="Pillow was built without WebP support",
)
def test_log_final_image_preserves_webp_file(
    tmp_path: Path, monkeypatch
) -> None:
    tracker, client = _create_tracker()
    path = tmp_path / "image_from_webp.webp"
    expected = _write_image(path, "WEBP")
    monkeypatch.chdir(tmp_path)

    tracker.log_final_image("image_from_webp", "image_from_webp.webp")

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "image_from_webp"
    assert filepath == "image_from_webp.webp"
    assert filename == "image_from_webp.webp"
    assert content == expected
    assert content_type == "image/webp"


@pytest.mark.skipif(
    not features.check("webp"),
    reason="Pillow was built without WebP support",
)
def test_log_final_artifact_preserves_webp_file(
    tmp_path: Path, monkeypatch
) -> None:
    tracker, client = _create_tracker()
    path = tmp_path / "artifact_image_from_webp.webp"
    expected = _write_image(path, "WEBP")
    monkeypatch.chdir(tmp_path)

    tracker.log_final_artifact("artifact_image_from_webp", path)

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "artifact_image_from_webp"
    assert filepath == "artifact_image_from_webp.webp"
    assert filename == "artifact_image_from_webp.webp"
    assert content == expected
    assert content_type == "image/webp"


def test_log_final_image_converts_image_like_content(monkeypatch) -> None:
    tracker, client = _create_tracker()
    image_like = object()
    converted: list[object] = []

    def fake_image_data_to_png_bytes(content: object) -> bytes:
        converted.append(content)
        return b"converted-png"

    monkeypatch.setattr(
        "experiment_tracker_sdk.utils.content_utils.image_data_to_png_bytes",
        fake_image_data_to_png_bytes,
    )

    tracker.log_final_image("preview", image_like)

    assert converted == [image_like]
    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "preview"
    assert filepath == "final/preview.png"
    assert filename == "preview.png"
    assert content == b"converted-png"
    assert content_type == "image/png"


def test_log_final_text_uploads_utf8_text() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_text("notes", "finished")

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "notes"
    assert filepath == "final/notes.txt"
    assert filename == "notes.txt"
    assert content == b"finished"
    assert content_type == "text/plain"


def test_log_final_text_uploads_bytes_with_default_path() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_text("notes_bytes", b"finished bytes")

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "notes_bytes"
    assert filepath == "final/notes_bytes.txt"
    assert filename == "notes_bytes.txt"
    assert content == b"finished bytes"
    assert content_type == "text/plain"


def test_log_final_json_serializes_dict() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_json("summary", {"accuracy": 0.9, "tags": ["final"]})

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "summary"
    assert filepath == "final/summary.json"
    assert filename == "summary.json"
    assert json.loads(content.decode("utf-8")) == {
        "accuracy": 0.9,
        "tags": ["final"],
    }
    assert content_type == "application/json"


def test_log_final_json_serializes_list() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_json("summary_list", [{"accuracy": 0.9}, {"loss": 0.1}])

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "summary_list"
    assert filepath == "final/summary_list.json"
    assert filename == "summary_list.json"
    assert json.loads(content.decode("utf-8")) == [
        {"accuracy": 0.9},
        {"loss": 0.1},
    ]
    assert content_type == "application/json"


def test_log_final_yaml_serializes_dict() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_yaml("config", {"run": {"steps": 3}, "enabled": True})

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "config"
    assert filepath == "final/config.yaml"
    assert filename == "config.yaml"
    assert content == b"run:\n  steps: 3\nenabled: true\n"
    assert content_type == "application/x-yaml"


def test_log_final_yaml_serializes_list() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_yaml("config_list", [{"name": "alpha"}, {"name": "beta"}])

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "config_list"
    assert filepath == "final/config_list.yaml"
    assert filename == "config_list.yaml"
    assert content == b"-\n  name: \"alpha\"\n-\n  name: \"beta\"\n"
    assert content_type == "application/x-yaml"


def test_log_final_text_file_path_uses_file_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    tracker, client = _create_tracker()
    path = tmp_path / "report.txt"
    path.write_text("from disk", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    tracker.log_final_text("report", "report.txt")

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "report"
    assert filepath == "report.txt"
    assert filename == "report.txt"
    assert content == b"from disk"
    assert content_type == "text/plain"
