from __future__ import annotations

import mimetypes
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeAlias

import pathspec
import pyrootutils
from experiment_tracker_shared import compute_file_sha256_hexdigest
from pydantic import BaseModel, Field

from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.artifact_client import ArtifactClient
from experiment_tracker_sdk.client.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.domain.experiment_data.dto import SnapshotFileEntry
from experiment_tracker_sdk.constants import DEFAULT_SNAPSHOT_MAX_FILE_SIZE_BYTES

SnapshotPathInput: TypeAlias = str | Path | Iterable[str | Path]
IgnoreFileInput: TypeAlias = str | Path | Iterable[str | Path]
SnapshotRootInput: TypeAlias = str | Path | None
DEFAULT_IGNORE_FILES = (".gitignore", ".exp_tracker_ignore")
DEFAULT_EXP_TRACKER_IGNORE_CONTENT = """# Experiment Tracker snapshot ignores
.env
.env.*
.venv/
venv/
env/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
logs/
runs/
wandb/
mlruns/
checkpoints/
node_modules/
.next/
dist/
build/
*.pyc
*.pyo
*.log
uv.lock
"""
DEFAULT_IGNORE_PATTERNS = [
    ".git/",
    ".gitignore",
    ".exp_tracker_ignore",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".venv/",
    "venv/",
    "env/",
    ".env/",
    ".env",
    ".env.*",
    "node_modules/",
    ".next/",
    "logs/",
    "dist/",
    "build/",
    "*.pyc",
    "*.pyo",
]


@dataclass(frozen=True)
class SnapshotScanFile:
    """File selected for inclusion in an experiment snapshot.

    Args:
        path: Absolute local filesystem path to upload.
        relative_path: POSIX-style path stored in the snapshot manifest.
        size: File size in bytes.

    Result:
        Immutable scan entry consumed by ``SnapshotUploader``.
    """

    path: Path
    relative_path: str
    size: int


SnapshotSkipReason: TypeAlias = Literal["ignored", "too_large", "not_file"]


@dataclass(frozen=True)
class SnapshotSkippedFile:
    """File or directory excluded from an experiment snapshot scan.

    Args:
        path: POSIX-style path relative to the snapshot root.
        reason: Reason the path was skipped, such as ignore rules, size limits,
            or non-regular-file detection.
        size: File size in bytes when available and relevant.

    Result:
        Immutable skip detail used by CLI summaries and diagnostics.
    """

    path: str
    reason: SnapshotSkipReason
    size: int | None = None


@dataclass(frozen=True)
class SnapshotScanResult:
    """Complete result of scanning local paths for snapshot upload.

    Args:
        root: Filesystem root used to compute manifest-relative paths.
        included: Files selected for upload and manifest inclusion.
        skipped: Sorted unique skipped paths for concise summaries.
        skipped_details: Detailed skip records including reasons and sizes.

    Result:
        Immutable scan result that separates uploadable files from exclusions.
    """

    root: Path
    included: list[SnapshotScanFile] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    skipped_details: list[SnapshotSkippedFile] = field(default_factory=list)


class SnapshotUploadResult(BaseModel):
    """Summary returned after logging a snapshot through the SDK.

    Args:
        snapshot_id: Backend/object-storage snapshot identifier returned by the
            API, if available.
        included: Number of files in the manifest.
        skipped: Number of paths omitted during local scanning.
        uploaded: Number of content-addressed blobs uploaded by this call.
        existing: Number of manifest files already present in project storage.

    Result:
        User-facing upload summary for ``ExpTracker.log_snapshot``.
    """

    snapshot_id: str | None = Field(default=None)
    included: int
    skipped: int
    uploaded: int
    existing: int


def normalize_ignore_files(ignore_file: IgnoreFileInput) -> tuple[str, ...]:
    """Normalize ignore-file configuration to an ordered tuple of names.

    Args:
        ignore_file: A single path/name or iterable of paths/names to read as
            gitwildmatch ignore files.

    Returns:
        Tuple of string paths preserving caller order.
    """
    if isinstance(ignore_file, str | Path):
        return (str(ignore_file),)
    return tuple(str(item) for item in ignore_file)


def normalize_snapshot_paths(path: SnapshotPathInput) -> tuple[Path, ...]:
    """Normalize snapshot path input into resolved filesystem paths.

    Args:
        path: Single path or iterable of paths to scan.

    Returns:
        Tuple of expanded, absolute ``Path`` objects.
    """
    if isinstance(path, str | Path):
        return (Path(path).expanduser().resolve(),)
    paths = tuple(Path(item).expanduser().resolve() for item in path)
    if not paths:
        raise ValueError("Snapshot paths cannot be empty")
    return paths


def normalize_snapshot_root(root: SnapshotRootInput) -> Path | None:
    """Normalize an explicit snapshot root.

    Args:
        root: Absolute directory used to compute manifest-relative paths, or
            ``None`` to discover the root from ignore files.

    Returns:
        Resolved absolute root path, or ``None``.
    """
    if root is None:
        return None
    root_path = Path(root).expanduser()
    if not root_path.is_absolute():
        raise ValueError(f"Snapshot root must be an absolute path: {root}")
    root_path = root_path.resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Snapshot root does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Snapshot root is not a directory: {root_path}")
    return root_path


def normalize_snapshot_max_file_size(max_file_size: int | None) -> int | None:
    """Convert snapshot size-limit input into an internal nullable limit.

    Args:
        max_file_size: Maximum allowed file size in bytes; ``None`` or negative
            values disable the limit.

    Returns:
        Positive byte limit, or ``None`` for unlimited snapshot file size.
    """
    if max_file_size is None or max_file_size < 0:
        return None
    return max_file_size


def create_exp_tracker_ignore(directory: str | Path, *, force: bool = False) -> Path:
    """Create the default ``.exp_tracker_ignore`` file in a directory.

    Args:
        directory: Existing directory where the ignore file should be created.
        force: Whether to overwrite an existing ignore file.

    Returns:
        Path to the created or pre-existing ignore file.
    """
    target_dir = Path(directory).expanduser().resolve()
    if not target_dir.exists():
        raise FileNotFoundError(f"Directory does not exist: {target_dir}")
    if not target_dir.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {target_dir}")
    target = target_dir / ".exp_tracker_ignore"
    if target.exists() and not force:
        return target
    target.write_text(DEFAULT_EXP_TRACKER_IGNORE_CONTENT, encoding="utf-8")
    return target


def _ignore_root_with_pyrootutils(
    start: Path,
    ignore_file: IgnoreFileInput,
) -> Path | None:
    """Find the nearest ancestor containing a configured ignore file.

    Args:
        start: Directory used as the starting point for pyrootutils search.
        ignore_file: Ignore-file name or names to locate.

    Returns:
        Directory containing a matching ignore file, or ``None`` when no
        configured ignore file applies.
    """
    indicators: list[str] = []
    for filename in normalize_ignore_files(ignore_file):
        ignore_path = Path(filename).expanduser()
        if ignore_path.is_absolute():
            ignore_path = ignore_path.resolve()
            if ignore_path.is_file() and _is_relative_to(start, ignore_path.parent):
                return ignore_path.parent
            continue
        indicators.append(str(ignore_path))
    if not indicators:
        return None
    try:
        return Path(
            pyrootutils.find_root(
                search_from=str(start),
                indicator=indicators,
            )
        ).resolve()
    except FileNotFoundError:
        return None


def _is_relative_to(path: Path, root: Path) -> bool:
    """Return whether ``path`` is inside or equal to ``root``.

    Args:
        path: Candidate path to test.
        root: Root directory that should contain the path.

    Returns:
        ``True`` when ``path.relative_to(root)`` succeeds, otherwise ``False``.
    """
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_scan_root(
    paths: tuple[Path, ...],
    ignore_file: IgnoreFileInput,
    root: SnapshotRootInput = None,
) -> Path:
    """Choose the root used for relative snapshot manifest paths.

    Args:
        paths: Resolved user-supplied paths being scanned.
        ignore_file: Ignore-file names that may move the root to a repository or
            tracker-ignore boundary.
        root: Explicit absolute root, or ``None`` to discover one.

    Returns:
        Directory used to compute relative paths for included and skipped files.
    """
    explicit_root = normalize_snapshot_root(root)
    if len(paths) == 1 and not paths[0].is_dir():
        fallback_root = paths[0].parent
    elif len(paths) == 1:
        fallback_root = paths[0]
    else:
        common_roots = [item if item.is_dir() else item.parent for item in paths]
        fallback_root = Path(os.path.commonpath([str(item) for item in common_roots]))

    resolved_root = (
        explicit_root
        or _ignore_root_with_pyrootutils(
            fallback_root,
            ignore_file,
        )
        or fallback_root
    )
    for snapshot_path in paths:
        if not _is_relative_to(snapshot_path, resolved_root):
            raise ValueError(
                f"Snapshot path is outside snapshot root: {snapshot_path} "
                f"not under {resolved_root}"
            )
    return resolved_root


def _read_ignore_patterns(root: Path, ignore_file: IgnoreFileInput) -> list[str]:
    """Read default and user-configured ignore patterns.

    Args:
        root: Snapshot root where relative ignore-file names are resolved.
        ignore_file: Ignore-file name or names to read.

    Returns:
        Ordered gitwildmatch pattern list used by ``pathspec``.
    """
    patterns = list(DEFAULT_IGNORE_PATTERNS)
    for filename in normalize_ignore_files(ignore_file):
        ignore_path = root / filename
        if ignore_path.is_file():
            patterns.extend(ignore_path.read_text(encoding="utf-8").splitlines())
    return patterns


def _build_spec(root: Path, ignore_file: IgnoreFileInput) -> pathspec.PathSpec:
    """Build the pathspec matcher for snapshot scanning.

    Args:
        root: Snapshot root where ignore files are read.
        ignore_file: Ignore-file name or names to include.

    Returns:
        ``PathSpec`` configured for gitwildmatch ignore semantics.
    """
    return pathspec.PathSpec.from_lines(
        "gitwildmatch",
        _read_ignore_patterns(root, ignore_file),
    )


def _posix_relative(path: Path, root: Path) -> str:
    """Format a path relative to the snapshot root using POSIX separators.

    Args:
        path: Absolute path to format.
        root: Root path that contains ``path``.

    Returns:
        Slash-separated relative path suitable for snapshot manifests.
    """
    return path.relative_to(root).as_posix()


def scan_snapshot_files(
    path: SnapshotPathInput = ".",
    *,
    root: SnapshotRootInput = None,
    ignore_file: IgnoreFileInput = DEFAULT_IGNORE_FILES,
    max_file_size: int | None = DEFAULT_SNAPSHOT_MAX_FILE_SIZE_BYTES,
) -> SnapshotScanResult:
    """Scan local files for an experiment snapshot manifest.

    Args:
        path: Single file/directory or iterable of files/directories to scan.
        root: Absolute directory used for manifest-relative paths. When
            ``None``, the root is discovered by searching ancestors for ignore
            files.
        ignore_file: Ignore-file names or paths read with gitwildmatch syntax.
        max_file_size: Maximum included file size in bytes; ``None`` or
            negative values allow any size.

    Returns:
        ``SnapshotScanResult`` containing included files, skipped paths, and
        detailed skip reasons.
    """
    paths = normalize_snapshot_paths(path)
    normalized_max_file_size = normalize_snapshot_max_file_size(max_file_size)
    for snapshot_path in paths:
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot path does not exist: {snapshot_path}")

    root = _resolve_scan_root(paths, ignore_file, root=root)

    if len(paths) == 1 and paths[0].is_file():
        size = paths[0].stat().st_size
        rel = _posix_relative(paths[0], root)
        if normalized_max_file_size is not None and size > normalized_max_file_size:
            skipped_file = SnapshotSkippedFile(
                path=rel,
                reason="too_large",
                size=size,
            )
            return SnapshotScanResult(
                root=root,
                skipped=[rel],
                skipped_details=[skipped_file],
            )
        return SnapshotScanResult(
            root=root,
            included=[
                SnapshotScanFile(
                    path=paths[0],
                    relative_path=rel,
                    size=size,
                )
            ],
        )

    spec = _build_spec(root, ignore_file)
    included: list[SnapshotScanFile] = []
    skipped_details: list[SnapshotSkippedFile] = []
    seen_files: set[Path] = set()

    def skip(
        relative_path: str,
        reason: SnapshotSkipReason,
        *,
        size: int | None = None,
    ) -> None:
        """Record a skipped path discovered during directory traversal.

        Args:
            relative_path: POSIX path relative to the scan root.
            reason: Skip reason to expose in diagnostics.
            size: Optional byte size for size-related skips.

        Returns:
            None. The function appends to ``skipped_details``.
        """
        skipped_details.append(
            SnapshotSkippedFile(path=relative_path, reason=reason, size=size)
        )

    def add_file(file_path: Path) -> None:
        """Add a regular file to the scan result if it passes size checks.

        Args:
            file_path: Filesystem path discovered from explicit input or walk.

        Returns:
            None. The function mutates ``included``, ``seen_files``, or
            ``skipped_details``.
        """
        resolved_file = file_path.resolve()
        if resolved_file in seen_files:
            return
        seen_files.add(resolved_file)
        rel = _posix_relative(resolved_file, root)
        size = resolved_file.stat().st_size
        if normalized_max_file_size is not None and size > normalized_max_file_size:
            skip(rel, "too_large", size=size)
            return
        included.append(
            SnapshotScanFile(
                path=resolved_file,
                relative_path=rel,
                size=size,
            )
        )

    for snapshot_path in paths:
        if snapshot_path.is_file():
            add_file(snapshot_path)
            continue
        if not snapshot_path.is_dir():
            skip(_posix_relative(snapshot_path, root), "not_file")
            continue

        for current_root, dirs, files in os.walk(snapshot_path):
            current = Path(current_root)
            kept_dirs = []
            for dirname in dirs:
                rel_dir = _posix_relative(current / dirname, root) + "/"
                if spec.match_file(rel_dir):
                    skip(rel_dir, "ignored")
                else:
                    kept_dirs.append(dirname)
            dirs[:] = kept_dirs

            for filename in files:
                file_path = current / filename
                rel = _posix_relative(file_path, root)
                if spec.match_file(rel):
                    skip(rel, "ignored")
                    continue
                if not file_path.is_file():
                    skip(rel, "not_file")
                    continue
                add_file(file_path)

    included.sort(key=lambda item: item.relative_path)
    skipped_details = sorted(
        set(skipped_details),
        key=lambda item: (item.path, item.reason, item.size or -1),
    )
    skipped = sorted({item.path for item in skipped_details})
    return SnapshotScanResult(
        root=root,
        included=included,
        skipped=skipped,
        skipped_details=skipped_details,
    )


def _content_type(path: Path) -> str:
    """Infer an upload content type for a snapshot file.

    Args:
        path: Local file path whose name is used for MIME type guessing.

    Returns:
        Guessed MIME type, or ``application/octet-stream`` when unknown.
    """
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


class SnapshotUploader:
    """Upload local snapshot files and register the manifest with the backend.

    Args:
        registry: Request-spec registry containing project-artifact and
            experiment-data endpoints.
        request_client: HTTP client used for the final snapshot metadata upsert.

    Result:
        Stateful helper used by ``ExpTracker`` to scan, upload, and log
        snapshots.
    """

    def __init__(
        self,
        *,
        registry: APIRequestsRegistry,
        request_client: ExperimentTrackerClient,
    ) -> None:
        """Initialize snapshot upload dependencies.

        Args:
            registry: API request registry for endpoint construction.
            request_client: SDK HTTP client used for API execution.

        Returns:
            None.
        """
        self._registry = registry
        self._request_client = request_client
        self._artifacts = ArtifactClient(registry, request_client)

    def log_snapshot(
        self,
        *,
        project_id: str,
        experiment_id: str,
        path: SnapshotPathInput = ".",
        root: SnapshotRootInput = None,
        ignore_file: IgnoreFileInput = DEFAULT_IGNORE_FILES,
        max_file_size: int | None = DEFAULT_SNAPSHOT_MAX_FILE_SIZE_BYTES,
        verbose: bool = False,
    ) -> SnapshotUploadResult:
        """Log a filesystem snapshot for one experiment.

        Args:
            project_id: Project whose content-addressed artifact store receives
                missing file blobs.
            experiment_id: Experiment whose snapshot metadata is upserted.
            path: File, directory, or iterable of paths to scan.
            root: Absolute directory used for manifest-relative paths, or
                ``None`` to discover one from ignore files.
            ignore_file: Ignore-file name or names applied during scanning.
            max_file_size: Maximum included file size in bytes; ``None`` or a
                negative value disables size filtering.
            verbose: Whether upload progress bars should be shown.

        Returns:
            ``SnapshotUploadResult`` summarizing included, skipped, uploaded,
            and already-existing files.
        """
        scan = scan_snapshot_files(
            path,
            root=root,
            ignore_file=ignore_file,
            max_file_size=max_file_size,
        )
        hashed_files = [
            (item, compute_file_sha256_hexdigest(item.path)) for item in scan.included
        ]
        hashes = [item_hash for _, item_hash in hashed_files]
        missing = set(
            self._artifacts.check_project_artifacts(project_id, hashes).missing
            if hashes
            else []
        )
        uploaded = 0
        existing = 0
        for item, item_hash in hashed_files:
            if item_hash not in missing:
                existing += 1
                continue
            with item.path.open("rb") as file_obj:
                upload_result = self._artifacts.upload_project_artifact(
                    project_id=project_id,
                    filename=item.path.name,
                    content=file_obj,
                    content_type=_content_type(item.path),
                    artifact_hash=item_hash,
                    size=item.size,
                    verbose=verbose,
                )
            if upload_result.detail == "uploaded":
                uploaded += 1
            else:
                existing += 1

        manifest = [
            SnapshotFileEntry(path=item.relative_path, hash=item_hash, size=item.size)
            for item, item_hash in hashed_files
        ]
        response = self._request_client.request(
            self._registry.experiment_data.upsert_snapshot(
                experiment_id=experiment_id,
                files=manifest,
            )
        )
        snapshot_id = getattr(response, "snapshot_id", None)
        return SnapshotUploadResult(
            snapshot_id=str(snapshot_id) if snapshot_id else None,
            included=len(scan.included),
            skipped=len(scan.skipped),
            uploaded=uploaded,
            existing=existing,
        )


def format_scan_lines(files: Iterable[SnapshotScanFile]) -> list[str]:
    """Format included files for CLI output.

    Args:
        files: Included scan entries to render.

    Returns:
        Tab-separated ``path`` and ``size`` lines.
    """
    return [f"{item.relative_path}\t{item.size}" for item in files]


def format_skipped_lines(skipped: Iterable[SnapshotSkippedFile]) -> list[str]:
    """Format skipped files for CLI output.

    Args:
        skipped: Detailed skip records to render.

    Returns:
        Tab-separated lines containing reason, path, and optional size.
    """
    lines: list[str] = []
    for item in skipped:
        size = "" if item.size is None else f"\t{item.size}"
        lines.append(f"{item.reason}\t{item.path}{size}")
    return lines


def format_scan_summary(scan: SnapshotScanResult) -> list[str]:
    """Format a high-level snapshot scan summary for CLI output.

    Args:
        scan: Completed scan result to summarize.

    Returns:
        Lines containing root path, included/skipped counts, and included file
        details.
    """
    return [
        f"root: {scan.root}",
        f"included: {len(scan.included)}",
        f"skipped: {len(scan.skipped)}",
        *format_scan_lines(scan.included),
    ]
