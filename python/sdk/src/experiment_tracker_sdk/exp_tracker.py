import re
import hashlib
import json
import mimetypes
import io
from pathlib import Path
from typing import cast
from uuid import UUID

from experiment_tracker_sdk.logger import logger
from experiment_tracker_sdk.client import API, ExperimentStatus, ExperimentTrackerClient
from experiment_tracker_sdk.client.domain.experiments.dto import ExperimentResponse
from experiment_tracker_sdk.client.domain.objects.dto import LogObjectRequest
from experiment_tracker_sdk.client.domain.projects.dto import ProjectResponse
from experiment_tracker_sdk.config import load_config
from experiment_tracker_sdk.error import ExpTrackerAPIError, ExpTrackerProgressError


class ExpTracker:
    """
    Minimal TensorBoard-like logging API.
    Methods mirror typical tensorboard.SummaryWriter calls:
        - add_scalar
        - add_scalars
        - add_image
        - add_text
        - add_histogram
        - add_audio
        - add_figure
        - add_mesh
        - add_embedding
        - flush
        - close
    """

    def __init__(self, experiment_id: str | UUID, project_id: str | UUID, api: API):
        """Initialize the ExpTracker instance.
        Args:
            log_dir (str): Directory to save logs or use as project/source.
            **kwargs: Additional arguments as needed.
        """
        self.experiment_id = experiment_id
        self.project_id = project_id
        self._api = api

        # Used to group scalars by step to reduce API calls (table have separate column per scalar name)
        self._last_logged_step = 0
        self._current_values: dict[str, float] = {}

    @staticmethod
    def _get_api_client() -> API:
        config = load_config()
        api = API(ExperimentTrackerClient(config.base_url, config.api_token))
        return api

    @classmethod
    def init(
        cls,
        project: str | UUID,
        experiment: str | UUID,
        try_existing_experiment: bool = True,
    ) -> "ExpTracker":
        """Initialize the ExpTracker instance.
        Args:
            project (str | UUID): The ID or name of the project.
            experiment (str | UUID): The ID or name of the experiment.
        """
        # Convert UUIDs to strings
        project = str(project)
        experiment = str(experiment)

        api = cls._get_api_client()
        projects = cast(
            list[ProjectResponse], api.request(api.projects.get_all_projects())
        )
        project_obj = next(
            (p for p in projects if p.name == project or p.id == project), None
        )
        if project_obj is None:
            raise ExpTrackerAPIError(f"Project not found: {project}")
        logger.info(f"Using project: {project_obj.id} with name {project_obj.name}")
        experiment_obj = None
        if try_existing_experiment:
            # Try to find an existing experiment with the given name or ID
            experiments = cast(
                list[ExperimentResponse],
                api.request(api.experiments.get_experiments_by_project(project_obj.id)),
            )
            experiment_obj = next(
                (e for e in experiments if e.name == experiment or e.id == experiment),
                None,
            )
            if experiment_obj is not None:
                logger.info(
                    f"Using experiment: {experiment_obj.id} with name {experiment_obj.name}"
                )
        if experiment_obj is None:
            # Create a new experiment
            logger.info(f"Creating new experiment: {experiment} for project: {project}")
            experiment_obj = cast(
                ExperimentResponse,
                api.request(
                    api.experiments.create_experiment(project_obj.id, experiment)
                ),
            )
        return cls(experiment_obj.id, project_obj.id, api)

    def add_scalar(
        self, tag: str, scalar_value, global_step: int = 0, walltime: float = 0
    ):
        """Log a single scalar value."""
        if global_step == self._last_logged_step:
            # We try to group scalars by step to reduce API calls (table have separate column per scalar name)
            self._current_values[tag] = scalar_value
        else:
            # We log the current values and reset the current values
            if self._current_values:
                self._api.queued_request(
                    self._api.scalars.log_scalar(
                        self.experiment_id, self._current_values, self._last_logged_step
                    )
                )
            self._last_logged_step = global_step
            self._current_values = {tag: scalar_value}

    def add_scalars(
        self,
        main_tag: str,
        tag_scalar_dict: dict,
        global_step: int = 0,
        walltime: float = 0,
    ):
        """Log multiple scalar values under a main tag."""
        for tag, scalar_value in tag_scalar_dict.items():
            self.add_scalar(main_tag + tag, scalar_value, global_step, walltime)

    def add_image(
        self,
        tag: str,
        img_tensor,
        global_step: int = 0,
        walltime: float = 0,
    ):
        """Upload and log a single image object.

        Supported inputs:
        - PIL.Image.Image
        - numpy.ndarray in HW or HWC layout
        """
        image_bytes = self._materialize_image_bytes(img_tensor)
        metadata = {"format": "png"}
        self._upload_and_log_object(
            tag=tag,
            object_type="image",
            content=image_bytes,
            global_step=global_step,
            metadata=metadata,
            default_extension=".png",
            default_content_type="image/png",
        )

    def add_text(
        self,
        tag: str,
        text_string: str,
        global_step: int = 0,
        walltime: float = 0,
    ):
        """Upload and log text as a text object."""
        self._upload_and_log_object(
            tag=tag,
            object_type="text",
            content=text_string,
            global_step=global_step,
            metadata={"encoding": "utf-8"},
            default_extension=".txt",
            default_content_type="text/plain",
        )

    def add_histogram(
        self,
        tag: str,
        values,
        global_step: int = 0,
        bins: int = 10,
        walltime: float = 0,
    ):
        """Log a histogram of values."""
        logger.warning("add_histogram is not implemented")

    def add_audio(
        self,
        tag: str,
        snd_tensor,
        global_step: int = 0,
        sample_rate: int = 44100,
        walltime: float = 0,
    ):
        """Upload and log audio object."""
        logger.warning("add_audio is not implemented")

    def add_figure(
        self,
        tag: str,
        figure,
        global_step: int = 0,
        close: bool = True,
        walltime: float = 0,
    ):
        """Log a matplotlib figure."""
        logger.warning("add_figure is not implemented")

    def add_mesh(
        self,
        tag: str,
        vertices,
        colors=None,
        faces=None,
        config_dict=None,
        global_step: int = 0,
        walltime: float = 0,
    ):
        """Upload and log 3D point cloud/mesh payload."""
        payload = {
            "vertices": vertices,
            "colors": colors,
            "faces": faces,
            "config": config_dict,
        }
        self._upload_and_log_object(
            tag=tag,
            object_type="point_cloud_3d",
            content=json.dumps(payload, default=str),
            global_step=global_step,
            metadata={"format": "json"},
            default_extension=".json",
            default_content_type="application/json",
        )

    def add_video(
        self,
        tag: str,
        vid_tensor,
        global_step: int = 0,
        walltime: float = 0,
        fps: int = 4,
    ):
        """Upload and log video object."""
        self._upload_and_log_object(
            tag=tag,
            object_type="video",
            content=vid_tensor,
            global_step=global_step,
            metadata={"fps": str(fps)},
            default_content_type="video/mp4",
        )

    def add_embedding(
        self,
        mat,
        metadata=None,
        label_img=None,
        global_step: int = 0,
        tag: str = "default",
        metadata_header=None,
    ):
        """Log embeddings."""
        logger.warning("add_embedding is not implemented")

    def progress(self, progress: int | float):
        """Update the progress of the experiment."""
        if isinstance(progress, int) and (progress < 0 or progress > 100):
            raise ExpTrackerProgressError(
                f"Progress must be between 0 and 100, got {progress}"
            )
        if isinstance(progress, float):
            if progress < 0 or progress > 1:
                raise ExpTrackerProgressError(
                    f"Progress must be between 0 and 1, got {progress}"
                )
            progress = round(progress * 100)
        self._api.queued_request(
            self._api.experiments.update_experiment(
                self.experiment_id, progress=progress
            )
        )

    def status(self, status: ExperimentStatus):
        """Update the status of the experiment."""
        self._api.queued_request(
            self._api.experiments.update_experiment(self.experiment_id, status=status)
        )

    def tags(self, *tags: str):
        """Update the tags of the experiment."""
        self._api.request(
            self._api.experiments.update_experiment(self.experiment_id, tags=list(tags))
        )

    def color(self, color: str):
        """Update the color of the experiment."""
        if not re.fullmatch(r"^#[0-9a-fA-F]{6}$", color):
            raise ExpTrackerAPIError(f"Invalid color: {color}")
        self._api.request(
            self._api.experiments.update_experiment(self.experiment_id, color=color)
        )

    def description(self, description: str):
        """Update the description of the experiment."""
        self._api.request(
            self._api.experiments.update_experiment(
                self.experiment_id, description=description
            )
        )

    def name(self, name: str):
        """Update the name of the experiment."""
        self._api.request(
            self._api.experiments.update_experiment(self.experiment_id, name=name)
        )

    def parent_experiment(self, parent_experiment: str | UUID):
        """Update the parent experiment of the experiment."""
        experiments = cast(
            list[ExperimentResponse],
            self._api.request(
                self._api.experiments.get_experiments_by_project(self.project_id)
            ),
        )
        parent_experiment_obj = next(
            (
                e
                for e in experiments
                if e.name == parent_experiment or e.id == parent_experiment
            ),
            None,
        )
        if parent_experiment_obj is None:
            raise ExpTrackerAPIError(
                f"Parent experiment not found: {parent_experiment}"
            )

        logger.info(
            f"Using parent experiment: {parent_experiment_obj.id} with name {parent_experiment_obj.name}"
        )
        self._api.request(
            self._api.experiments.update_experiment(
                self.experiment_id, parent_experiment_id=parent_experiment_obj.id
            )
        )

    def flush(self):
        """Flush the event file to disk/network."""
        if self._current_values:
            self._api.queued_request(
                self._api.scalars.log_scalar(
                    self.experiment_id, self._current_values, self._last_logged_step
                )
            )
            self._last_logged_step = 0
            self._current_values = {}
        self._api.flush()

    def close(self):
        """Close the logger and free resources."""
        if self._current_values:
            self._api.queued_request(
                self._api.scalars.log_scalar(
                    self.experiment_id, self._current_values, self._last_logged_step
                )
            )
            self._last_logged_step = 0
            self._current_values = {}
        self._api.flush()
        self._api.close()

    def _upload_and_log_object(
        self,
        tag: str,
        object_type: str,
        content,
        global_step: int,
        metadata: dict[str, str] | None = None,
        default_extension: str = "",
        default_content_type: str = "application/octet-stream",
    ) -> None:
        try:
            # 1) Convert user input (bytes/path/file-like/tensor-like) into a binary (bytes) payload.
            file_name, content_bytes, content_type = self._materialize_content(
                tag=tag,
                step=global_step,
                content=content,
                default_extension=default_extension,
                default_content_type=default_content_type,
            )
            # 2) Use content hash as stable object reference (dedup key in object storage).
            blob_hash = hashlib.sha256(content_bytes).hexdigest()
            # 3) Check if this blob already exists to avoid re-uploading identical content.
            check_result = self._api.check_blobs([blob_hash])
            missing_hashes = set(check_result.get("missing", []))
            if blob_hash in missing_hashes:
                self._api.upload_blob(blob_hash, file_name, content_bytes, content_type)
            # 4) Log lightweight metadata row to objects API (stored in scalars_service table).
            payload_metadata = {
                "filename": file_name,
                "content_type": content_type,
                "size_bytes": str(len(content_bytes)),
            }
            if metadata:
                payload_metadata.update(metadata)
            self._api.queued_request(
                self._api.objects.log_object(
                    self.experiment_id,
                    LogObjectRequest(
                        name=tag,
                        # Object type drives frontend rendering branch (image/video/audio/text/3d).
                        object_type=object_type,  # type: ignore[arg-type]
                        # Path keeps object-storage reference; currently this is the blob hash.
                        path=blob_hash,
                        step=global_step,
                        metadata=payload_metadata,
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to upload/log object '{tag}': {exc}")

    def _materialize_content(
        self,
        tag: str,
        step: int,
        content,
        default_extension: str,
        default_content_type: str,
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
            file_name = f"{tag}_{step}{default_extension}"
            return file_name, content, default_content_type
        # String can be either a filesystem path or plain text payload.
        if isinstance(content, (str, Path)):
            path = Path(content)
            if path.exists() and path.is_file() or isinstance(content, Path):
                file_name = path.name
                content_bytes = path.read_bytes()
                guessed_type = mimetypes.guess_type(file_name)[0]
                return (
                    file_name,
                    content_bytes,
                    guessed_type or default_content_type,
                )
            # If the content is a string and not a path, we assume it is a plain text payload.
            file_name = f"{tag}_{step}{default_extension or '.txt'}"
            return file_name, content.encode("utf-8"), "text/plain"
        # File-like object with .read() support.
        if hasattr(content, "read") and callable(content.read):
            raw = content.read()
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
            if isinstance(raw, bytes):
                file_name = f"{tag}_{step}{default_extension}"
                return file_name, raw, default_content_type
        # Tensor/array-like object exposing .tobytes() for zero-copy binary extraction.
        if hasattr(content, "tobytes") and callable(content.tobytes):
            raw = content.tobytes()
            if isinstance(raw, bytes):
                file_name = f"{tag}_{step}{default_extension}"
                return file_name, raw, default_content_type
        raise ExpTrackerAPIError(
            "Unsupported content type. Use bytes, file path, file-like, or string."
        )

    def _materialize_image_bytes(self, image_input) -> bytes:
        """Convert PIL image or numpy ndarray to PNG bytes.

        ndarray contract:
        - layout must be HW or HWC
        - HW is expanded to RGB (3 channels)
        - HWC supports only 3 (RGB) or 4 (RGBA) channels
        - float dtypes are normalized to [0, 1] (min-max if out of range), then scaled to uint8
        - non-uint8 integer-like dtypes are clipped to [0, 255] and cast to uint8
        """
        try:
            import numpy as np  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            raise ExpTrackerAPIError(
                "numpy is required for image logging. Install numpy to use add_image."
            ) from exc

        try:
            from PIL import Image  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            raise ExpTrackerAPIError(
                "Pillow is required for image logging. Install pillow to use add_image."
            ) from exc

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
