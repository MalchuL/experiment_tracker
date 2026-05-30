"""Large deterministic JSON artifacts for verbose transfer demos."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FORMAT_ID = "experiment-tracker-verbose-demo"
FORMAT_VERSION = 1


@dataclass(frozen=True)
class StructuredJsonInfo:
    """Summary of a parsed demo JSON artifact."""

    path: Path
    artifact_index: int
    file_size: int
    record_count: int
    first_record_id: int
    last_record_id: int
    first_metric: float
    last_metric: float


def _record(artifact_index: int, record_index: int) -> dict[str, Any]:
    record_id = artifact_index * 1_000_000 + record_index
    return {
        "id": record_id,
        "step": record_index,
        "metric": round(((record_id % 10_000) / 10_000.0) * 3.141592653589793, 12),
        "phase": "train" if record_index % 2 == 0 else "val",
    }


def _document_shell(artifact_index: int, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "format": FORMAT_ID,
        "version": FORMAT_VERSION,
        "artifact_index": artifact_index,
        "record_count": len(records),
        "records": records,
    }


def _serialize(document: dict[str, Any]) -> bytes:
    return json.dumps(document, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def build_json_document(artifact_index: int, min_bytes: int) -> dict[str, Any]:
    """Build a JSON object with enough records to reach at least ``min_bytes``."""
    # Calibrate bytes-per-record from a small sample (avoid O(n^2) re-serialization).
    sample_count = 32
    sample_records = [_record(artifact_index, i) for i in range(sample_count)]
    sample_bytes = len(_serialize(_document_shell(artifact_index, sample_records)))
    shell_overhead = sample_bytes - sum(
        len(json.dumps(record, separators=(",", ":"), ensure_ascii=True).encode())
        for record in sample_records
    )
    bytes_per_record = max(1, (sample_bytes - shell_overhead) // sample_count)

    record_count = max(sample_count, (min_bytes - shell_overhead) // bytes_per_record + 1024)
    records = [_record(artifact_index, i) for i in range(record_count)]
    document = _document_shell(artifact_index, records)

    while len(_serialize(document)) < min_bytes:
        grow_by = max(10_000, (min_bytes - len(_serialize(document))) // bytes_per_record + 1)
        start = len(records)
        records.extend(
            _record(artifact_index, i) for i in range(start, start + grow_by)
        )
        document = _document_shell(artifact_index, records)

    return document


def write_structured_json(
    path: Path, artifact_index: int, min_bytes: int
) -> StructuredJsonInfo:
    """Write compact UTF-8 JSON of at least ``min_bytes``."""
    document = build_json_document(artifact_index, min_bytes)
    payload = _serialize(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return parse_structured_json(path)


def parse_structured_json(path: Path) -> StructuredJsonInfo:
    """Load and validate the demo JSON schema."""
    raw = path.read_bytes()
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc

    if not isinstance(document, dict):
        raise ValueError(f"{path}: root must be a JSON object")
    if document.get("format") != FORMAT_ID:
        raise ValueError(f"{path}: unexpected format {document.get('format')!r}")
    if document.get("version") != FORMAT_VERSION:
        raise ValueError(f"{path}: unexpected version {document.get('version')!r}")

    artifact_index = document.get("artifact_index")
    if not isinstance(artifact_index, int) or artifact_index < 0:
        raise ValueError(f"{path}: invalid artifact_index")

    record_count = document.get("record_count")
    records = document.get("records")
    if not isinstance(record_count, int) or record_count < 1:
        raise ValueError(f"{path}: invalid record_count")
    if not isinstance(records, list) or len(records) != record_count:
        raise ValueError(f"{path}: records length does not match record_count")

    expected_first = _record(artifact_index, 0)
    expected_last = _record(artifact_index, record_count - 1)
    if records[0] != expected_first:
        raise ValueError(f"{path}: first record does not match deterministic layout")
    if records[-1] != expected_last:
        raise ValueError(f"{path}: last record does not match deterministic layout")
    if record_count > 2:
        mid = record_count // 2
        if records[mid] != _record(artifact_index, mid):
            raise ValueError(f"{path}: middle record does not match deterministic layout")

    first = records[0]
    last = records[-1]
    return StructuredJsonInfo(
        path=path,
        artifact_index=artifact_index,
        file_size=len(raw),
        record_count=record_count,
        first_record_id=int(first["id"]),
        last_record_id=int(last["id"]),
        first_metric=float(first["metric"]),
        last_metric=float(last["metric"]),
    )


def load_json_document(path: Path) -> dict[str, Any]:
    """Return the parsed JSON object (for deep equality checks)."""
    document = json.loads(path.read_bytes())
    if not isinstance(document, dict):
        raise ValueError(f"{path}: root must be a JSON object")
    return document


def structured_json_infos_equal(
    left: StructuredJsonInfo, right: StructuredJsonInfo
) -> bool:
    """Return True when parsed summaries describe the same artifact."""
    return (
        left.artifact_index == right.artifact_index
        and left.file_size == right.file_size
        and left.record_count == right.record_count
        and left.first_record_id == right.first_record_id
        and left.last_record_id == right.last_record_id
        and left.first_metric == right.first_metric
        and left.last_metric == right.last_metric
    )
