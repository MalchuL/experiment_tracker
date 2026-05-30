from __future__ import annotations

from pathlib import Path

import pytest

from experiment_tracker_sdk.client.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.request_types import (
    ApiRequestSpec,
    FileDownloadResponse,
    FileDownloadToPathItem,
    FileUploadItem,
    FileUploadSpec,
)
from experiment_tracker_sdk.client.transport.options import RequestOptions
from experiment_tracker_sdk.client.utils.transfer_progress import (
    ProgressBytesReader,
    content_length_from_headers,
)


def test_progress_bytes_reader_reports_reads() -> None:
    data = b"abcdefghij"
    seen: list[int] = []

    reader = ProgressBytesReader(data, on_read=seen.append)
    assert reader.read(4) == b"abcd"
    assert reader.read(4) == b"efgh"
    assert reader.read() == b"ij"
    assert reader.read(1) == b""
    assert seen == [4, 4, 2]


def test_content_length_from_headers() -> None:
    assert content_length_from_headers({"content-length": "1024"}) == 1024
    assert content_length_from_headers({}) is None
    assert content_length_from_headers({"content-length": "nope"}) is None


def test_executor_upload_uses_progress_reader_when_verbose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"ok": "true"}

        headers: dict[str, str] = {}

    class FakeClient:
        def request(self, *_args: object, **kwargs: object) -> FakeResponse:
            files = kwargs["files"]
            assert isinstance(files, dict)
            file_field = files["file"]
            captured["file_field"] = file_field
            return FakeResponse()

    client = ExperimentTrackerClient(
        base_url="http://127.0.0.1:8000",
        api_token="token",
    )
    monkeypatch.setattr(client, "_http_client", FakeClient())

    payload = b"hello-world"
    spec = ApiRequestSpec(
        method="POST",
        endpoint="/upload",
        query_params={"hash": "abc"},
        files={
            "file": FileUploadSpec(
                filename="demo.bin",
                content=payload,
                content_type="application/octet-stream",
            )
        },
    )
    client.request(spec, options=RequestOptions(verbose=True))

    file_field = captured["file_field"]
    assert isinstance(file_field, tuple)
    assert file_field[0] == "demo.bin"
    reader = file_field[1]
    assert isinstance(reader, ProgressBytesReader)
    assert reader.read() == payload


def test_executor_download_verbose_streams_with_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks = [b"part-a", b"part-b"]

    class FakeStreamResponse:
        headers = {"content-length": "11", "content-disposition": 'filename="x.bin"'}

        def iter_bytes(self) -> list[bytes]:
            return chunks

        def raise_for_status(self) -> None:
            return None

    class FakeStreamContext:
        def __enter__(self) -> FakeStreamResponse:
            return FakeStreamResponse()

        def __exit__(self, *_args: object) -> None:
            return None

    class FakeClient:
        def stream(self, *_args: object, **_kwargs: object) -> FakeStreamContext:
            return FakeStreamContext()

    client = ExperimentTrackerClient(
        base_url="http://127.0.0.1:8000",
        api_token="token",
    )
    monkeypatch.setattr(client, "_http_client", FakeClient())

    spec = ApiRequestSpec(
        method="GET",
        endpoint="/download",
        query_params={"name": "weights"},
        response_model=FileDownloadResponse,
    )
    download = client.request(
        spec,
        options=RequestOptions(verbose=True),
    )
    assert isinstance(download, FileDownloadResponse)
    assert download.filename == "x.bin"
    assert b"".join(download.content) == b"part-apart-b"


def test_upload_files_batch_calls_executor_per_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_execute(self, _http_client, spec: ApiRequestSpec, options=None):  # noqa: ANN001
        assert spec.files is not None
        calls.append(spec.files["file"].filename)
        return {"filename": spec.files["file"].filename}

    from experiment_tracker_sdk.client.transport.executor import HttpRequestExecutor

    monkeypatch.setattr(HttpRequestExecutor, "execute", fake_execute)
    client = ExperimentTrackerClient(
        base_url="http://127.0.0.1:8000",
        api_token="token",
    )
    results = client.upload_files_batch(
        endpoint="/upload",
        items=[
            FileUploadItem(params={"id": "1"}, filename="a.bin", content=b"a"),
            FileUploadItem(params={"id": "2"}, filename="b.bin", content=b"b"),
        ],
    )
    assert calls == ["a.bin", "b.bin"]
    assert len(results) == 2


def test_download_files_batch_to_paths_writes_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_execute(self, _http_client, spec: ApiRequestSpec, options=None):  # noqa: ANN001
        return FileDownloadResponse(
            content=b"payload",
            filename="saved.bin",
            content_type="application/octet-stream",
        )

    from experiment_tracker_sdk.client.transport.executor import HttpRequestExecutor

    monkeypatch.setattr(HttpRequestExecutor, "execute", fake_execute)
    client = ExperimentTrackerClient(
        base_url="http://127.0.0.1:8000",
        api_token="token",
    )
    out_a = tmp_path / "a.bin"
    out_b = tmp_path / "b.bin"
    paths = client.download_files_batch_to_paths(
        endpoint="/download",
        items=[
            FileDownloadToPathItem(output_path=str(out_a)),
            FileDownloadToPathItem(output_path=str(out_b), params={"name": "b"}),
        ],
    )
    assert paths == [out_a, out_b]
    assert out_a.read_bytes() == b"payload"
    assert out_b.read_bytes() == b"payload"
