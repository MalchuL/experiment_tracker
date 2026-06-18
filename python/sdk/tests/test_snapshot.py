import os
from types import SimpleNamespace

import pytest

from experiment_tracker_sdk.client.domain.project_artifacts.dto import (
    CheckProjectArtifactsResponse,
)
from experiment_tracker_sdk.snapshot import (
    DEFAULT_SNAPSHOT_MAX_FILE_SIZE_BYTES,
    SnapshotUploader,
    normalize_snapshot_max_file_size,
    scan_snapshot_files,
)
from experiment_tracker_sdk.utils.parallel import (
    ParallelTaskRunner,
    default_parallel_worker_count,
)


def test_scan_snapshot_files_uses_gitignore_and_exp_tracker_ignore(tmp_path):
    """Verify snapshot scanning honors both Git and tracker ignore files.

    Args:
        tmp_path: Temporary snapshot root populated with included and ignored
            files.

    Returns:
        None. The assertions check included paths, skipped paths, and skip
        reasons.
    """
    (tmp_path / ".gitignore").write_text(
        "ignored-by-git.txt\nlogs/\n",
        encoding="utf-8",
    )
    (tmp_path / ".exp_tracker_ignore").write_text(
        "ignored-by-tracker.txt\n", encoding="utf-8"
    )
    (tmp_path / "included.txt").write_text("keep", encoding="utf-8")
    (tmp_path / "ignored-by-git.txt").write_text("skip", encoding="utf-8")
    (tmp_path / "ignored-by-tracker.txt").write_text("skip", encoding="utf-8")
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "train.log").write_text("skip", encoding="utf-8")

    scan = scan_snapshot_files(tmp_path)

    assert [item.relative_path for item in scan.included] == ["included.txt"]
    assert ".gitignore" in scan.skipped
    assert ".exp_tracker_ignore" in scan.skipped
    assert "ignored-by-git.txt" in scan.skipped
    assert "ignored-by-tracker.txt" in scan.skipped
    assert "logs/" in scan.skipped
    assert {item.reason for item in scan.skipped_details} == {"ignored"}


def test_scan_snapshot_files_accepts_explicit_ignore_file_list(tmp_path):
    """Verify custom ignore-file lists are applied in caller-specified order.

    Args:
        tmp_path: Temporary snapshot root containing custom ignore files.

    Returns:
        None. The assertions check ignored files are skipped while ignore files
        themselves remain upload candidates.
    """
    (tmp_path / "first.ignore").write_text("first.txt\n", encoding="utf-8")
    (tmp_path / "second.ignore").write_text("second.txt\n", encoding="utf-8")
    (tmp_path / "first.txt").write_text("skip", encoding="utf-8")
    (tmp_path / "second.txt").write_text("skip", encoding="utf-8")
    (tmp_path / "included.txt").write_text("keep", encoding="utf-8")

    scan = scan_snapshot_files(
        tmp_path,
        ignore_file=("first.ignore", "second.ignore"),
    )

    assert [item.relative_path for item in scan.included] == [
        "first.ignore",
        "included.txt",
        "second.ignore",
    ]
    assert "first.txt" in scan.skipped
    assert "second.txt" in scan.skipped


def test_scan_snapshot_files_accepts_multiple_paths(tmp_path):
    """Verify scanning multiple directories uses their common parent root.

    Args:
        tmp_path: Temporary parent directory containing two snapshot inputs.

    Returns:
        None. The assertions check root selection and stable relative paths.
    """
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    (first_dir / "a.txt").write_text("a", encoding="utf-8")
    (second_dir / "b.txt").write_text("b", encoding="utf-8")

    scan = scan_snapshot_files((first_dir, second_dir))

    assert scan.root == tmp_path
    assert [item.relative_path for item in scan.included] == [
        "first/a.txt",
        "second/b.txt",
    ]


def test_scan_snapshot_files_accepts_explicit_absolute_root(tmp_path):
    """Verify callers can pin the manifest root explicitly."""
    root = tmp_path / "repo"
    package_dir = root / "package"
    package_dir.mkdir(parents=True)
    (root / ".exp_tracker_ignore").write_text("ignored.txt\n", encoding="utf-8")
    (package_dir / "included.py").write_text("print('ok')", encoding="utf-8")

    scan = scan_snapshot_files(package_dir, root=root)

    assert scan.root == root
    assert [item.relative_path for item in scan.included] == ["package/included.py"]


def test_scan_snapshot_files_uses_ancestor_ignore_with_explicit_child_root(tmp_path):
    """Verify explicit child roots still discover ignore files above them."""
    repo = tmp_path / "repo"
    package_dir = repo / "package"
    package_dir.mkdir(parents=True)
    (repo / ".exp_tracker_ignore").write_text(
        "ignored.py\n/package/root-relative.py\n",
        encoding="utf-8",
    )
    (package_dir / "included.py").write_text("print('ok')", encoding="utf-8")
    (package_dir / "ignored.py").write_text("print('skip')", encoding="utf-8")
    (package_dir / "root-relative.py").write_text("print('skip')", encoding="utf-8")

    scan = scan_snapshot_files(package_dir, root=package_dir)

    assert scan.root == package_dir
    assert [item.relative_path for item in scan.included] == ["included.py"]
    assert "ignored.py" in scan.skipped
    assert "root-relative.py" in scan.skipped


def test_scan_snapshot_files_list_path_uses_parent_ignore_with_explicit_root(tmp_path):
    """Verify list inputs with explicit child roots still use parent ignores."""
    workspace = tmp_path / "training_files"
    workspace.mkdir()
    (tmp_path / ".exp_tracker_ignore").write_text(
        "ignored.py\n/training_files/root-relative.py\n",
        encoding="utf-8",
    )
    (workspace / "included.py").write_text("print('ok')", encoding="utf-8")
    (workspace / "ignored.py").write_text("print('skip')", encoding="utf-8")
    (workspace / "root-relative.py").write_text("print('skip')", encoding="utf-8")

    scan = scan_snapshot_files([workspace], root=workspace.absolute())

    assert scan.root == workspace
    assert [item.relative_path for item in scan.included] == ["included.py"]
    assert scan.skipped == ["ignored.py", "root-relative.py"]


def test_scan_snapshot_files_rejects_relative_root(tmp_path):
    """Verify explicit roots must be absolute paths."""
    (tmp_path / "included.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="Snapshot root must be an absolute path"):
        scan_snapshot_files(tmp_path, root="relative-root")


def test_scan_snapshot_files_accepts_absolute_ignore_file_for_root(tmp_path):
    """Verify absolute ignore-file paths can still establish the root."""
    ignore_path = tmp_path / ".exp_tracker_ignore"
    ignore_path.write_text("ignored.txt\n", encoding="utf-8")
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "included.py").write_text("print('ok')", encoding="utf-8")

    scan = scan_snapshot_files(package_dir, ignore_file=ignore_path)

    assert scan.root == tmp_path
    assert [item.relative_path for item in scan.included] == ["package/included.py"]


def test_scan_snapshot_files_accepts_mixed_file_and_directory_paths(tmp_path):
    """Verify scanning mixed explicit files and directories.

    Args:
        tmp_path: Temporary root containing one explicit file and one directory
            input.

    Returns:
        None. The assertions check included paths and ignore-rule handling for
        directory contents.
    """
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (tmp_path / ".exp_tracker_ignore").write_text("src/ignored.txt\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (src_dir / "included.py").write_text("print('ok')", encoding="utf-8")
    (src_dir / "ignored.txt").write_text("skip", encoding="utf-8")

    scan = scan_snapshot_files((tmp_path / "README.md", src_dir))

    assert scan.root == tmp_path
    assert [item.relative_path for item in scan.included] == [
        "README.md",
        "src/included.py",
    ]
    assert "src/ignored.txt" in scan.skipped


def test_scan_snapshot_files_deduplicates_overlapping_paths(tmp_path):
    """Verify overlapping input paths do not duplicate manifest entries.

    Args:
        tmp_path: Temporary root containing a directory and an explicitly listed
            file inside it.

    Returns:
        None. The assertion checks the file appears once in scan results.
    """
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    file_path = src_dir / "included.py"
    file_path.write_text("print('ok')", encoding="utf-8")

    scan = scan_snapshot_files((src_dir, file_path))

    assert [item.relative_path for item in scan.included] == ["included.py"]


def test_scan_snapshot_files_uses_nearest_ignore_file_as_root(tmp_path):
    """Verify a nearby ignore file establishes the snapshot root.

    Args:
        tmp_path: Temporary repository-like root containing a nested package.

    Returns:
        None. The assertions check root selection and root-relative ignored
        paths.
    """
    (tmp_path / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "included.py").write_text("print('ok')", encoding="utf-8")
    (package_dir / "ignored.tmp").write_text("skip", encoding="utf-8")

    scan = scan_snapshot_files(package_dir)

    assert scan.root == tmp_path
    assert [item.relative_path for item in scan.included] == ["package/included.py"]
    assert "package/ignored.tmp" in scan.skipped


def test_scan_snapshot_files_uses_nearest_ignore_root_for_single_file(tmp_path):
    """Verify single-file scans still search ancestors for tracker ignores.

    Args:
        tmp_path: Temporary root containing ``.exp_tracker_ignore`` and a nested
            explicit file.

    Returns:
        None. The assertions check the ancestor ignore root is used.
    """
    (tmp_path / ".exp_tracker_ignore").write_text("ignored.txt\n", encoding="utf-8")
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    file_path = package_dir / "included.py"
    file_path.write_text("print('ok')", encoding="utf-8")

    scan = scan_snapshot_files(file_path)

    assert scan.root == tmp_path
    assert [item.relative_path for item in scan.included] == ["package/included.py"]


def test_scan_snapshot_files_honors_ignore_for_single_file(tmp_path):
    """Verify single-file scans still apply discovered ignore files."""
    (tmp_path / ".exp_tracker_ignore").write_text("ignored.py\n", encoding="utf-8")
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    file_path = package_dir / "ignored.py"
    file_path.write_text("print('skip')", encoding="utf-8")

    scan = scan_snapshot_files(file_path)

    assert scan.root == tmp_path
    assert scan.included == []
    assert scan.skipped == ["package/ignored.py"]


def test_scan_snapshot_files_skips_files_above_max_size(tmp_path):
    """Verify files larger than the configured maximum are skipped.

    Args:
        tmp_path: Temporary root containing small and oversized files.

    Returns:
        None. The assertions check included paths and detailed ``too_large``
        skip metadata.
    """
    small = tmp_path / "small.txt"
    large = tmp_path / "large.txt"
    small.write_text("12345", encoding="utf-8")
    large.write_text("123456", encoding="utf-8")

    scan = scan_snapshot_files(tmp_path, max_file_size=5)

    assert [item.relative_path for item in scan.included] == ["small.txt"]
    assert "large.txt" in scan.skipped
    assert [(item.path, item.reason, item.size) for item in scan.skipped_details] == [
        ("large.txt", "too_large", 6)
    ]


def test_scan_snapshot_files_allows_unlimited_max_size(tmp_path):
    """Verify ``max_file_size=-1`` disables snapshot size filtering.

    Args:
        tmp_path: Temporary root containing a file larger than the default
            snapshot limit.

    Returns:
        None. The assertion checks the large file is included.
    """
    large = tmp_path / "large.txt"
    large.write_bytes(b"x" * (DEFAULT_SNAPSHOT_MAX_FILE_SIZE_BYTES + 1))

    scan = scan_snapshot_files(tmp_path, max_file_size=-1)

    assert [item.relative_path for item in scan.included] == ["large.txt"]


def test_normalize_snapshot_max_file_size_treats_none_as_unlimited():
    """Verify snapshot size normalization maps unlimited values to ``None``.

    Args:
        None. The test calls the normalizer directly.

    Returns:
        None. The assertions check ``None``, negative, and positive inputs.
    """
    assert normalize_snapshot_max_file_size(None) is None
    assert normalize_snapshot_max_file_size(-1) is None
    assert normalize_snapshot_max_file_size(10) == 10


def test_scan_snapshot_files_reports_not_file_reason(tmp_path):
    """Verify non-regular files are reported with the ``not_file`` reason.

    Args:
        tmp_path: Temporary root used to create a FIFO when supported.

    Returns:
        None. The assertions check skipped path and detailed reason metadata.
    """
    if not hasattr(os, "mkfifo"):
        pytest.skip("mkfifo is not available on this platform")
    fifo = tmp_path / "named-pipe"
    os.mkfifo(fifo)

    scan = scan_snapshot_files(fifo)

    assert scan.skipped == ["named-pipe"]
    assert [(item.path, item.reason, item.size) for item in scan.skipped_details] == [
        ("named-pipe", "not_file", None)
    ]


def test_snapshot_uploader_streams_files_and_closes_handles(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify snapshot uploads stream file handles and close them afterwards.

    Args:
        tmp_path: Temporary root containing a file to snapshot.
        monkeypatch: Pytest helper used to replace the artifact client class.

    Returns:
        None. The assertions check upload counts and handle closure.
    """
    file_path = tmp_path / "weights.bin"
    file_path.write_bytes(b"payload")
    uploaded_handles = []
    snapshot_files = []

    class FakeArtifacts:
        """Artifact-client fake that records streamed upload handles.

        Args:
            *_args: Positional constructor arguments ignored by the fake.
            **_kwargs: Keyword constructor arguments ignored by the fake.

        Result:
            Test double implementing project artifact check and upload methods.
        """

        def __init__(self, *_args, **_kwargs) -> None:
            """Accept artifact-client construction arguments.

            Args:
                *_args: Positional constructor arguments.
                **_kwargs: Keyword constructor arguments.

            Returns:
                None.
            """
            pass

        def check_project_artifacts(self, _project_id, hashes):
            """Report all supplied hashes as missing from project storage.

            Args:
                _project_id: Project identifier ignored by the fake.
                hashes: Hashes the uploader wants to check.

            Returns:
                ``CheckProjectArtifactsResponse`` marking every hash missing.
            """
            return CheckProjectArtifactsResponse(missing=hashes)

        def upload_project_artifact(self, **kwargs):
            """Validate streamed upload content and record the open file handle.

            Args:
                **kwargs: Upload parameters passed by ``SnapshotUploader``.

            Returns:
                Simple object whose ``detail`` marks the upload as successful.
            """
            content = kwargs["content"]
            assert not content.closed
            assert content.read() == b"payload"
            assert kwargs["artifact_hash"]
            assert kwargs["size"] == len(b"payload")
            uploaded_handles.append(content)
            return SimpleNamespace(detail="uploaded")

    class FakeExperimentData:
        """Experiment-data request factory fake for snapshot upserts.

        Args:
            None. The fake is stateless.

        Result:
            Object exposing ``upsert_snapshot`` for the registry fake.
        """

        def upsert_snapshot(self, **kwargs):
            """Echo snapshot upsert parameters as a request spec placeholder.

            Args:
                **kwargs: Upsert parameters provided by ``SnapshotUploader``.

            Returns:
                The keyword arguments unchanged.
            """
            snapshot_files.extend(kwargs["files"])
            return kwargs

    class FakeClient:
        """Request-client fake returning a snapshot identifier.

        Args:
            None. The fake is stateless.

        Result:
            Object exposing ``request`` for ``SnapshotUploader``.
        """

        def request(self, _spec):
            """Return a synthetic response for the final snapshot upsert.

            Args:
                _spec: Request specification ignored by the fake.

            Returns:
                Object with ``snapshot_id`` set to ``snapshot-1``.
            """
            return SimpleNamespace(snapshot_id="snapshot-1")

    from experiment_tracker_sdk import snapshot as snapshot_module

    monkeypatch.setattr(snapshot_module, "ArtifactClient", FakeArtifacts)
    uploader = SnapshotUploader(
        registry=SimpleNamespace(experiment_data=FakeExperimentData()),
        request_client=FakeClient(),
    )

    result = uploader.log_snapshot(
        project_id="project-1",
        experiment_id="experiment-1",
        path=tmp_path,
        max_file_size=None,
    )

    assert result.uploaded == 1
    assert snapshot_files[0].size == len(b"payload")
    assert uploaded_handles
    assert uploaded_handles[0].closed


def test_default_parallel_worker_count_uses_min_four_cpus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify default worker count caps at four cores."""
    import os

    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    assert default_parallel_worker_count() == 4

    monkeypatch.setattr(os, "cpu_count", lambda: 2)
    assert default_parallel_worker_count() == 2

    monkeypatch.setattr(os, "cpu_count", lambda: None)
    assert default_parallel_worker_count() == 1


def test_parallel_task_runner_preserves_order() -> None:
    """Verify parallel map preserves input order."""
    runner = ParallelTaskRunner(max_workers=4)
    assert runner.map(lambda value: value * 2, [1, 2, 3, 4]) == [2, 4, 6, 8]


def test_snapshot_uploader_uploads_multiple_files_in_parallel(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify snapshot uploads can process multiple missing files concurrently."""
    import threading

    (tmp_path / "first.bin").write_bytes(b"first")
    (tmp_path / "second.bin").write_bytes(b"second")
    (tmp_path / "third.bin").write_bytes(b"third")
    active_uploads = 0
    max_active_uploads = 0
    lock = threading.Lock()
    snapshot_files = []

    class FakeArtifacts:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def check_project_artifacts(self, _project_id, hashes):
            return CheckProjectArtifactsResponse(missing=hashes)

        def upload_project_artifact(self, **kwargs):
            nonlocal active_uploads, max_active_uploads
            with lock:
                active_uploads += 1
                max_active_uploads = max(max_active_uploads, active_uploads)
            try:
                content = kwargs["content"]
                assert not content.closed
                assert content.read()
                return SimpleNamespace(detail="uploaded")
            finally:
                with lock:
                    active_uploads -= 1

    class FakeExperimentData:
        def upsert_snapshot(self, **kwargs):
            snapshot_files.extend(kwargs["files"])
            return kwargs

    class FakeClient:
        def request(self, _spec):
            return SimpleNamespace(snapshot_id="snapshot-1")

    from experiment_tracker_sdk import snapshot as snapshot_module

    monkeypatch.setattr(snapshot_module, "ArtifactClient", FakeArtifacts)
    uploader = SnapshotUploader(
        registry=SimpleNamespace(experiment_data=FakeExperimentData()),
        request_client=FakeClient(),
    )

    result = uploader.log_snapshot(
        project_id="project-1",
        experiment_id="experiment-1",
        path=tmp_path,
        max_file_size=None,
        max_workers=3,
    )

    assert result.uploaded == 3
    assert result.existing == 0
    assert max_active_uploads >= 2
    assert {entry.path for entry in snapshot_files} == {
        "first.bin",
        "second.bin",
        "third.bin",
    }
