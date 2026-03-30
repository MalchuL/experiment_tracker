import io
import mimetypes
from pathlib import Path

from experiment_tracker_sdk.error import ExpTrackerAPIError


def materialize_content(
    content: bytes | str | Path | io.BytesIO | io.StringIO,
    file_name: str | None = None,
    mime_type: str | None = None,
) -> tuple[str, bytes, str]:
    """Convert user input into an upload-ready tuple: (file_name, bytes, content_type).

    Purpose of each return item:
    - file_name:
        Sent as multipart filename when uploading blob, and stored in metadata for UI/debug.
    - bytes:
        Actual binary payload uploaded to object storage and hashed for deduplication.
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
        if file_name is None:
            raise ExpTrackerAPIError("file_name is required when content is bytes")
        if mime_type is None:
            raise ExpTrackerAPIError("mime_type is required when content is bytes")
        return file_name, content, mime_type
    # String can be either a filesystem path or plain text payload.
    if isinstance(content, (str, Path)):
        path = Path(content)
        if path.exists() and path.is_file() or isinstance(content, Path):
            file_name = path.name
            content_bytes = path.read_bytes()
            guessed_type = mimetypes.guess_type(file_name)[0] or mime_type
            if guessed_type is None:
                raise ExpTrackerAPIError(
                    "mime_type is required when content is a string"
                )
            return (
                file_name,
                content_bytes,
                guessed_type,
            )
        # If the content is a string and not a path, we assume it is a plain text payload.
        if file_name is None:
            raise ExpTrackerAPIError("file_name is required when content is a string")
        return file_name, content.encode("utf-8"), mime_type or "text/plain"
    # File-like object with .read() support.
    if hasattr(content, "read") and callable(content.read):
        raw = content.read()
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if isinstance(raw, bytes):
            if file_name is None:
                raise ExpTrackerAPIError(
                    "file_name is required when content is a file-like object"
                )
            if mime_type is None:
                raise ExpTrackerAPIError(
                    "mime_type is required when content is a file-like object"
                )
            return file_name, raw, mime_type
    raise ExpTrackerAPIError(
        "Unsupported content type. Use bytes, file path, file-like, or string."
    )


def data_to_image_bytes(image_input) -> bytes:
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
