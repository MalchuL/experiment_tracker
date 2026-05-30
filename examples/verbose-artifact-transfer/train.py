from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from experiment_tracker_sdk import ExpTracker, ExperimentStatus, InitParams, config
from experiment_tracker_sdk.client.request_types import FileDownloadToPathItem
from experiment_tracker_sdk.client.transport.options import RequestOptions

from structured_json import (
    StructuredJsonInfo,
    load_json_document,
    parse_structured_json,
    structured_json_infos_equal,
    write_structured_json,
)

logger = logging.getLogger("verbose_artifact_transfer")

MIN_FILE_BYTES = 50 * 1024 * 1024
COMPARE_CHUNK_BYTES = 8 * 1024 * 1024
DOWNLOAD_ENDPOINT = "/experiment-artifacts/download"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upload and download several large (>=50 MiB) JSON experiment "
            "artifacts with tqdm progress bars (verbose mode)."
        )
    )
    parser.add_argument("--project-name", default="SDK Verbose Artifacts")
    parser.add_argument("--experiment-name", default="Large transfer demo")
    parser.add_argument("--team-name", default=None)
    parser.add_argument(
        "--artifact-count",
        type=int,
        default=3,
        help="Number of large files to upload and download (default: 3).",
    )
    parser.add_argument(
        "--file-size-mib",
        type=int,
        default=55,
        help="Minimum size of each JSON file in MiB (must be >= 50).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(".data"),
        help="Directory for generated upload files and downloaded copies.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Only upload artifacts; do not download them back.",
    )
    return parser.parse_args()


def _file_size_bytes(file_size_mib: int) -> int:
    if file_size_mib < 50:
        raise SystemExit("--file-size-mib must be at least 50 (50 MiB minimum).")
    return file_size_mib * 1024 * 1024


def _files_byte_equal(source: Path, dest: Path) -> bool:
    """Return True when both files have identical length and byte content."""
    src_size = source.stat().st_size
    dst_size = dest.stat().st_size
    if src_size != dst_size:
        return False
    with source.open("rb") as uploaded, dest.open("rb") as downloaded:
        while True:
            left = uploaded.read(COMPARE_CHUNK_BYTES)
            right = downloaded.read(COMPARE_CHUNK_BYTES)
            if left != right:
                return False
            if not left:
                return True


def _format_json_summary(info: StructuredJsonInfo) -> str:
    return (
        f"index={info.artifact_index} records={info.record_count} "
        f"size={info.file_size} bytes "
        f"ids=[{info.first_record_id}..{info.last_record_id}]"
    )


def _verify_download(
    sources: list[Path],
    destinations: list[Path],
    expected: list[StructuredJsonInfo],
) -> None:
    """Byte-compare and deep JSON equality for each downloaded artifact."""
    if len(sources) != len(destinations) or len(sources) != len(expected):
        raise RuntimeError("source, destination, and expected metadata counts differ")

    print("\n=== Verifying downloads ===\n", file=sys.stderr)
    for source, dest, uploaded_info in zip(sources, destinations, expected, strict=True):
        if not _files_byte_equal(source, dest):
            raise RuntimeError(
                f"byte mismatch for {dest.name}: {source} and {dest} differ"
            )

        downloaded_info = parse_structured_json(dest)
        if not structured_json_infos_equal(uploaded_info, downloaded_info):
            raise RuntimeError(
                f"structured summary mismatch for {dest.name}:\n"
                f"  upload:   {_format_json_summary(uploaded_info)}\n"
                f"  download: {_format_json_summary(downloaded_info)}"
            )

        uploaded_doc = load_json_document(source)
        downloaded_doc = load_json_document(dest)
        if uploaded_doc != downloaded_doc:
            raise RuntimeError(
                f"JSON content mismatch for {dest.name}: parsed objects are not equal"
            )

        logger.info(
            "verified_download",
            extra={
                "file": dest.name,
                "bytes": downloaded_info.file_size,
                "artifact_index": downloaded_info.artifact_index,
                "record_count": downloaded_info.record_count,
            },
        )
        print(
            f"  OK  {dest.name}\n"
            f"      bytes identical; JSON deep-equal\n"
            f"      {_format_json_summary(downloaded_info)}",
            file=sys.stderr,
        )


def main() -> None:
    args = _parse_args()
    if config.load_config() is None:
        raise SystemExit("SDK config not found. Run `experiment-tracker init`.")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    min_bytes = _file_size_bytes(args.file_size_mib)
    if args.artifact_count < 1:
        raise SystemExit("--artifact-count must be at least 1.")

    upload_dir = args.data_dir / "uploads"
    download_dir = args.data_dir / "downloads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    if not args.skip_download:
        download_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "preparing_json_files",
        extra={
            "artifact_count": args.artifact_count,
            "min_bytes": min_bytes,
            "upload_dir": str(upload_dir),
        },
    )

    print("\n=== Writing local JSON payloads ===\n", file=sys.stderr)
    local_paths: list[Path] = []
    stored_paths: list[str] = []
    json_infos: list[StructuredJsonInfo] = []
    for index in range(args.artifact_count):
        filename = f"large_blob_{index:02d}.json"
        local_path = upload_dir / filename
        stored_path = f"large/{filename}"
        info = write_structured_json(local_path, index, min_bytes)
        if info.file_size < MIN_FILE_BYTES:
            raise RuntimeError(
                f"{local_path} is {info.file_size} bytes; need at least {MIN_FILE_BYTES}"
            )
        local_paths.append(local_path)
        stored_paths.append(stored_path)
        json_infos.append(info)
        logger.info(
            "local_file_ready",
            extra={"path": str(local_path), "summary": _format_json_summary(info)},
        )
        print(f"  wrote {filename}: {_format_json_summary(info)}", file=sys.stderr)

    tracker: ExpTracker | None = None
    try:
        tracker = ExpTracker.init(
            project=args.project_name,
            experiment=args.experiment_name,
            team=args.team_name,
            init_params=InitParams(
                create_team_if_not_exists=True,
                create_project_if_not_exists=True,
                create_experiment_if_not_exists=True,
            ),
            verbose=True,
        )
        experiment_id = str(tracker.experiment_id)
        logger.info(
            "tracker_initialized",
            extra={
                "project_id": str(tracker.project_id),
                "experiment_id": experiment_id,
                "verbose_uploads": True,
            },
        )

        tracker.status(ExperimentStatus.RUNNING)
        tracker.tags("verbose-artifact-transfer", "large-files", "structured-json")

        print("\n=== Uploading artifacts (verbose) ===\n", file=sys.stderr)
        for index, (local_path, stored_path) in enumerate(
            zip(local_paths, stored_paths, strict=True)
        ):
            tag = f"large_blob_{index:02d}"
            logger.info(
                "upload_start",
                extra={"tag": tag, "stored_filepath": stored_path},
            )
            # verbose=None would use tracker.verbose; pass True per large file.
            tracker.log_final_artifact(
                tag,
                local_path,
                stored_filepath=stored_path,
                default_content_type="application/json",
                default_extension=".json",
                verbose=True,
            )
            logger.info("upload_done", extra={"tag": tag})

        tracker.flush()

        if args.skip_download:
            tracker.status(ExperimentStatus.COMPLETE)
            tracker.progress(100)
            logger.info("upload_only_complete", extra={"experiment_id": experiment_id})
            return

        client = tracker._request_client
        download_items = [
            FileDownloadToPathItem(
                output_path=str(download_dir / local_path.name),
                params={
                    "experiment_id": experiment_id,
                    "filepath": stored_path,
                },
                label=local_path.name,
            )
            for local_path, stored_path in zip(local_paths, stored_paths, strict=True)
        ]

        print("\n=== Downloading artifacts (verbose) ===\n", file=sys.stderr)
        saved_paths = client.download_files_batch_to_paths(
            endpoint=DOWNLOAD_ENDPOINT,
            items=download_items,
            options=RequestOptions(verbose=True),
        )

        _verify_download(local_paths, saved_paths, json_infos)

        tracker.status(ExperimentStatus.COMPLETE)
        tracker.progress(100)
        logger.info(
            "transfer_complete",
            extra={
                "experiment_id": experiment_id,
                "artifacts": len(saved_paths),
                "download_dir": str(download_dir),
            },
        )
        print(
            f"\nDone: {len(saved_paths)} JSON artifacts downloaded to {download_dir}, "
            "byte-identical and deep-equal to uploads.\n",
            file=sys.stderr,
        )
    except Exception:
        if tracker is not None:
            try:
                tracker.status(ExperimentStatus.FAILED)
            except Exception:
                logger.exception("failed_to_mark_experiment_failed")
        logger.exception("verbose_artifact_transfer_failed")
        raise
    finally:
        if tracker is not None:
            try:
                tracker.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
