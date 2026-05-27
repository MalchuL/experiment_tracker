import io
import json
import os
import mimetypes
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, IO, TypeAlias, TypeGuard, cast
from uuid import uuid4

from experiment_tracker_sdk.error import ExpTrackerAPIError

FinalArtifactContent = bytes | str | Path | IO[bytes] | IO[str]
StructuredFinalArtifactContent = (
    FinalArtifactContent | Mapping[str, Any] | list[Any] | tuple[Any, ...]
)

if TYPE_CHECKING:
    import numpy as np  # type: ignore[reportMissingImports]
    from PIL import Image as PILImage  # type: ignore[reportMissingImports]

    ImageDataContent: TypeAlias = PILImage.Image | np.ndarray
    ImageContent: TypeAlias = FinalArtifactContent | ImageDataContent
else:
    ImageDataContent: TypeAlias = Any
    ImageContent: TypeAlias = Any


@dataclass(frozen=True)
class PreparedArtifactContent:
    """Upload-ready content and metadata shared by step and final artifacts."""

    content: bytes
    filename: str
    content_type: str


@dataclass(frozen=True)
class PreparedFinalArtifact:
    """Upload-ready final artifact content plus tracked storage filepath."""

    content: bytes
    filename: str
    content_type: str
    filepath: str


def is_file_like_content(content: object) -> bool:
    """Return true for supported readable file-like artifact inputs."""
    return callable(getattr(content, "read", None))


def is_materialized_final_artifact_content(
    content: object,
) -> TypeGuard[FinalArtifactContent]:
    """Return true when content is already bytes, a path, text, or a readable file."""
    return isinstance(content, bytes | str | Path) or is_file_like_content(content)


def _yaml_key(value: Any) -> str:
    """Format a mapping key for the lightweight YAML serializer."""
    text = str(value)
    if text.replace("_", "").replace("-", "").isalnum():
        return text
    return json.dumps(text, ensure_ascii=False)


def _yaml_scalar(value: Any) -> str:
    """Format a scalar or compact empty collection as YAML-compatible text."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, Mapping):
        return "{}" if not value else json.dumps(value, default=str, ensure_ascii=False)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return "[]" if not value else json.dumps(value, default=str, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)


def _yaml_lines(value: Any, indent: int = 0) -> list[str]:
    """Render simple mapping/list/scalar values as indented YAML lines."""
    prefix = " " * indent
    if isinstance(value, Mapping):
        if not value:
            return [f"{prefix}{{}}"]
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, Mapping) and item:
                lines.append(f"{prefix}{_yaml_key(key)}:")
                lines.extend(_yaml_lines(item, indent + 2))
            elif (
                isinstance(item, Sequence)
                and not isinstance(item, str | bytes | bytearray)
                and item
            ):
                lines.append(f"{prefix}{_yaml_key(key)}:")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}{_yaml_key(key)}: {_yaml_scalar(item)}")
        return lines
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        if not value:
            return [f"{prefix}[]"]
        lines = []
        for item in value:
            if isinstance(item, Mapping) and item:
                lines.append(f"{prefix}-")
                lines.extend(_yaml_lines(item, indent + 2))
            elif (
                isinstance(item, Sequence)
                and not isinstance(item, str | bytes | bytearray)
                and item
            ):
                lines.append(f"{prefix}-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_yaml_scalar(item)}")
        return lines
    return [f"{prefix}{_yaml_scalar(value)}"]


def to_yaml_text(value: Any) -> str:
    """Serialize simple structured values to YAML text without extra dependencies."""
    return "\n".join(_yaml_lines(value)) + "\n"


def _safe_default_filename(name: str, default_extension: str | None = None) -> str:
    """Build a filesystem-safe default filename from a logical artifact name."""
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    if not filename:
        filename = uuid4().hex
    if default_extension:
        extension = default_extension if default_extension.startswith(".") else f".{default_extension}"
        # ``tag`` is a logical artifact name, not a user-provided filename.
        # The extension is only for the derived fallback upload path.
        if not filename.endswith(extension):
            filename = f"{filename}{extension}"
    return filename


def _max_path_length() -> int:
    """Upper bound for paths we will pass to ``Path(...).exists()`` (POSIX ``PC_PATH_MAX``)."""
    try:
        return int(os.pathconf(".", "PC_PATH_MAX"))
    except (OSError, ValueError):
        return 4096


def _is_existing_file_path(content: str | Path) -> bool:
    """True only when ``content`` refers to an existing regular file.

    Long ``str`` values (e.g. JSON or YAML bodies) are never probed with ``stat()``,
    avoiding ``OSError: [Errno 36] File name too long`` when the whole payload is
    mistaken for a filesystem path.
    """
    if not isinstance(content, (str, Path)):
        return False
    try:
        path_str = os.fspath(content)
    except (OSError, TypeError, ValueError):
        return False
    if len(path_str) > _max_path_length():
        return False
    try:
        path = Path(content)
        return path.exists() and path.is_file()
    except (OSError, ValueError):
        return False


def materialize_content(
    content: bytes | str | Path | IO[bytes] | IO[str],
    default_file_name: str | None = None,
    default_mime_type: str | None = None,
) -> tuple[bytes, str, str]:
    """Convert user input into an upload-ready tuple: (bytes, file_name, content_type).
    Args:
        content (bytes | str | Path | IO[bytes] | IO[str]): The content to materialize.
        default_file_name (str | None): The default file name to use if not retrieved from the content.
        default_mime_type (str | None): The default MIME type to use if not retrieved from the content.
    Returns:
        tuple[bytes, str, str]: A tuple containing the bytes, file name, and MIME type.
    Raises:
        ExpTrackerAPIError: If the content is not supported or the file name or MIME type is not retrieved from the content.

    Purpose of each return item:
    - bytes:
        Actual binary payload uploaded to object storage and hashed for deduplication.
    - file_name:
        Sent as multipart filename when uploading blob, and stored in metadata for UI/debug.
    - content_type (MIME):
        Used as HTTP Content-Type for the multipart file part.
        Also persisted in metadata, so downstream consumers (frontend/renderers)
        can decide how to display object (image/video/audio/text fallback).

    Note:
    `content_type` is not used for hash calculation (hash is computed from raw bytes),
    but it is important for transport semantics and later rendering.
    """
    # Raw bytes were provided directly by user code.
    if isinstance(content, bytes):
        if default_file_name is None:
            raise ExpTrackerAPIError("file_name is required when content is bytes")
        if default_mime_type is None:
            raise ExpTrackerAPIError("mime_type is required when content is bytes")
        return content, default_file_name, default_mime_type
    # String can be either a filesystem path or plain text payload.
    if isinstance(content, (str, Path)):
        path = Path(content)
        read_as_file = False
        if isinstance(content, Path):
            try:
                read_as_file = path.is_file()
            except (OSError, ValueError):
                read_as_file = False
            if not read_as_file:
                raise ExpTrackerAPIError(
                    "When content is pathlib.Path it must refer to an existing regular file."
                )
        else:
            read_as_file = _is_existing_file_path(content)

        if read_as_file:
            file_name = path.name
            content_bytes = path.read_bytes()
            guessed_type = mimetypes.guess_type(file_name)[0] or default_mime_type
            if guessed_type is None:
                raise ExpTrackerAPIError(
                    "mime_type is required when content is a string"
                )
            return (
                content_bytes,
                file_name,
                guessed_type,
            )
        # Plain str payload (not an on-disk file path).
        if default_file_name is None:
            raise ExpTrackerAPIError("file_name is required when content is a string")
        if isinstance(content, str):
            return (
                content.encode("utf-8"),
                default_file_name,
                default_mime_type or "text/plain",
            )
    # File-like object with .read() support.
    if (
        not isinstance(content, (str, Path))
        and hasattr(content, "read")
        and callable(content.read)
    ):
        read_content = content.read()
        if isinstance(read_content, str):
            content_bytes = read_content.encode("utf-8")
        elif isinstance(read_content, bytes):
            content_bytes = read_content
        else:
            content_bytes = None
        if content_bytes is not None:
            if default_file_name is None:
                raise ExpTrackerAPIError(
                    "file_name is required when content is a file-like object"
                )
            if default_mime_type is None:
                raise ExpTrackerAPIError(
                    "mime_type is required when content is a file-like object"
                )
            return content_bytes, default_file_name, default_mime_type
    raise ExpTrackerAPIError(
        "Unsupported content type. Use bytes, file path, file-like, or string."
    )


def prepare_final_artifact_content(
    *,
    tag: str,
    content: FinalArtifactContent,
    stored_filepath: str | None = None,
    default_content_type: str = "application/octet-stream",
    default_extension: str | None = None,
) -> PreparedFinalArtifact:
    """Resolve content, filename, MIME type, and tracked filepath for final uploads."""
    filename = _safe_default_filename(tag, default_extension)
    filepath = stored_filepath or (
        f"final/{filename}" if default_extension else filename
    )
    resolved_content_type = default_content_type
    guessed_content_type, _ = mimetypes.guess_type(filename)
    if guessed_content_type is not None:
        resolved_content_type = guessed_content_type
    elif isinstance(content, str):
        resolved_content_type = "text/plain"

    if isinstance(content, str | Path) and _is_existing_file_path(content):
        path = Path(content)
        filename = path.name
        if stored_filepath is None:
            try:
                filepath = str(path.resolve().relative_to(Path.cwd().resolve()))
            except ValueError:
                filepath = path.name

    content_bytes, _, content_type = materialize_content(
        content=content,
        default_file_name=filename,
        default_mime_type=resolved_content_type,
    )
    return PreparedFinalArtifact(
        content=content_bytes,
        filename=filename,
        content_type=content_type,
        filepath=filepath,
    )


def prepare_final_image_content(content: ImageContent) -> FinalArtifactContent:
    """Return direct image content or convert image-like data to PNG bytes."""
    if is_materialized_final_artifact_content(content):
        return content
    return image_data_to_png_bytes(cast("ImageDataContent", content))


def prepare_final_json_content(
    content: StructuredFinalArtifactContent,
    *,
    indent: int | None = 2,
) -> FinalArtifactContent:
    """Return JSON upload content, serializing structured values."""
    if isinstance(content, Mapping) or isinstance(content, list | tuple):
        return json.dumps(content, indent=indent, default=str)
    return content


def prepare_final_yaml_content(
    content: StructuredFinalArtifactContent,
) -> FinalArtifactContent:
    """Return YAML upload content, serializing structured values."""
    if isinstance(content, Mapping) or isinstance(content, list | tuple):
        return to_yaml_text(content).encode("utf-8")
    if isinstance(content, str) and not _is_existing_file_path(content):
        return content.encode("utf-8")
    return content


def prepare_step_image_content(
    tag: str, image_input: ImageDataContent, step: int
) -> PreparedArtifactContent:
    """Convert image-like step artifact input to upload-ready PNG content."""
    return PreparedArtifactContent(
        filename=f"{tag}_{step}.png",
        content=image_data_to_png_bytes(image_input),
        content_type="image/png",
    )


def prepare_step_text_content(
    tag: str, text: str, step: int
) -> PreparedArtifactContent:
    """Convert text step artifact input to upload-ready UTF-8 content."""
    return PreparedArtifactContent(
        filename=f"{tag}_{step}.txt",
        content=text.encode("utf-8"),
        content_type="text/plain",
    )


def image_data_to_png_bytes(image_input: ImageDataContent) -> bytes:
    """Convert PIL image or numpy ndarray to PNG bytes.

    ndarray contract:
    - layout must be HW or HWC
    - HW is expanded to RGB (3 channels)
    - HWC supports only 3 (RGB) or 4 (RGBA) channels
    - float dtypes are normalized to [0, 1] (min-max if out of range), then scaled to uint8
    - non-uint8 integer-like dtypes are clipped to [0, 255] and cast to uint8
    """
    errors = []
    try:
        import numpy as np  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        errors.append(
            f"numpy is required for image logging. Install numpy to use add_image. Error: {exc}"
        )

    try:
        from PIL import Image  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        errors.append(
            f"Pillow is required for image logging. Install pillow to use add_image. Error: {exc}"
        )

    if errors:
        raise ExpTrackerAPIError(
            f"Failed to import experiment tracker dependencies. Errors: {errors}"
        )

    image = None
    if isinstance(image_input, Image.Image):
        # Ensure stable color modes for serialization.
        if image_input.mode == "RGBA":
            image = image_input
        elif "A" in image_input.getbands():
            image = image_input.convert("RGBA")
        else:
            image = image_input.convert("RGB")
    elif isinstance(image_input, np.ndarray):
        arr = np.asarray(image_input)
        if arr.ndim == 2:
            # HW grayscale -> RGB by channel replication.
            arr = np.repeat(arr[..., None], 3, axis=2)
        elif arr.ndim == 3:
            channels = int(arr.shape[2])
            if channels not in (3, 4):
                raise ExpTrackerAPIError(
                    f"Unsupported HWC channel count: {channels}. Only 3 (RGB) or 4 (RGBA) are supported."
                )
        else:
            raise ExpTrackerAPIError(
                f"Unsupported ndarray shape {arr.shape}. Expected HW or HWC."
            )

        if np.issubdtype(arr.dtype, np.floating):
            arr = arr.astype(np.float32)
            finite_mask = np.isfinite(arr)
            if not finite_mask.any():
                raise ExpTrackerAPIError("Image array contains no finite values.")
            finite_values = arr[finite_mask]
            arr_min = float(finite_values.min())
            arr_max = float(finite_values.max())
            # If values are outside [0, 1], normalize using min-max.
            if arr_min < 0.0 or arr_max > 1.0:
                if arr_max == arr_min:
                    arr = np.zeros_like(arr, dtype=np.float32)
                else:
                    arr = (arr - arr_min) / (arr_max - arr_min)
            arr = np.clip(arr, 0.0, 1.0)
            arr = (arr * 255.0).round().astype(np.uint8)
        elif arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)

        mode = "RGBA" if arr.shape[2] == 4 else "RGB"
        image = Image.fromarray(arr, mode=mode)
    else:
        raise ExpTrackerAPIError(
            "Unsupported image type. add_image accepts PIL.Image.Image or numpy.ndarray."
        )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
