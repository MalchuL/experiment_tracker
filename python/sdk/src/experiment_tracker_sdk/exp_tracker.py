import math
import mimetypes
import re
from pathlib import Path
from typing import cast
from uuid import UUID

from experiment_tracker_sdk.api_access import ExpTrackerApiAccess
from experiment_tracker_sdk.client import (
    ExperimentStatus,
    ExperimentTrackerClient,
)
from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.blob_api import BlobRequestsStrategy
from experiment_tracker_sdk.client.constants import UNSET
from experiment_tracker_sdk.client.scalar_batching_strategy import (
    BatchedScalarLoggingStrategy,
)
from experiment_tracker_sdk.client.domain.experiments.dto import (
    ExperimentListResponse,
    ExperimentResponse,
    FeatureNodeLike,
)
from experiment_tracker_sdk.client.domain.projects.dto import (
    ProjectListResponse,
)
from experiment_tracker_sdk.error import ExpTrackerAPIError
from experiment_tracker_sdk.logger import logger
from experiment_tracker_sdk.utils.content_utils import (
    _is_existing_file_path,
    image_data_to_png_bytes,
    materialize_content,
)


class ExpTracker:
    """
    Minimal TensorBoard-like logging API.
    Methods mirror typical tensorboard.SummaryWriter calls:
        - add_scalar
        - add_metric
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

    def __init__(
        self,
        experiment_id: str | UUID,
        project_id: str | UUID,
        api_requests_registry: APIRequestsRegistry,
        request_client: ExperimentTrackerClient,
    ):
        """Initialize the ExpTracker instance.
        Args:
            log_dir (str): Directory to save logs or use as project/source.
            **kwargs: Additional arguments as needed.
        """
        self.experiment_id = experiment_id
        self.project_id = project_id
        self._api_requests_registry = api_requests_registry
        self._request_client = request_client
        self._blob_api = BlobRequestsStrategy(
            registry=api_requests_registry,
            request_client=request_client,
        )
        self._scalar_logging = BatchedScalarLoggingStrategy(
            experiment_id=experiment_id,
            registry=api_requests_registry,
            request_client=request_client,
        )

    @staticmethod
    def _get_api_requests_registry() -> APIRequestsRegistry:
        return ExpTrackerApiAccess.instance().get_api_requests_registry()

    @staticmethod
    def _get_request_client() -> ExperimentTrackerClient:
        return ExpTrackerApiAccess.instance().get_request_client()

    def _upload_artifact_at_step(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict | None = None,
    ):
        return self._blob_api.upload_and_log_experiment_artifact_at_step(
            experiment_id=str(self.experiment_id),
            filename=filename,
            content=content,
            content_type=content_type,
            name=name,
            artifact_type=artifact_type,
            step=step,
            metadata=metadata,
        )

    @classmethod
    def init(
        cls,
        project: str | UUID,
        experiment: str | UUID,
        try_existing_experiment: bool = True,
        features: list[FeatureNodeLike] | None = None,
    ) -> "ExpTracker":
        """Initialize the ExpTracker instance.
        Args:
            project (str | UUID): The ID or name of the project.
            experiment (str | UUID): The ID or name of the experiment.
        """
        # Convert UUIDs to strings
        project = str(project)
        experiment = str(experiment)

        api_requests_registry = cls._get_api_requests_registry()
        request_client = cls._get_request_client()

        projects = cast(
            ProjectListResponse,
            request_client.request(api_requests_registry.projects.get_all_projects()),
        ).data
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
                ExperimentListResponse,
                request_client.request(
                    api_requests_registry.experiments.get_experiments_by_project(
                        project_obj.id
                    )
                ),
            ).data
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
                request_client.request(
                    api_requests_registry.experiments.create_experiment(
                        project_obj.id,
                        experiment,
                        features=features if features is not None else UNSET,
                    )
                ),
            )
        return cls(
            experiment_obj.id,
            project_obj.id,
            api_requests_registry,
            request_client,
        )

    def add_scalar(
        self, tag: str, scalar_value, global_step: int = 0, walltime: float = 0
    ):
        """Log a single scalar value."""
        # TODO: Add NaN and Inf handling in the future for scalars service.
        if not isinstance(scalar_value, (int, float)) or not math.isfinite(
            scalar_value
        ):
            logger.warning(
                f"Invalid scalar value: {scalar_value} for tag: {tag}, global_step: {global_step}, not logged"
            )
            return
        self._scalar_logging.add_scalar(tag, float(scalar_value), global_step)

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

    def add_metric(
        self,
        name: str,
        value: float,
        label: str | None = None,
        walltime: float = 0,
    ):
        """Create or update a metric row for this (name, label) (sync mode, no queue)."""
        _ = walltime  # Kept for API parity with add_scalar-like signatures.
        if not math.isfinite(value):
            logger.warning(
                f"Invalid metric value: {value} for name: {name}, not logged"
            )
            return
        self._request_client.request(
            self._api_requests_registry.metrics.upsert_metric(
                experiment_id=self.experiment_id,
                name=name,
                value=value,
                label=label,
            )
        )

    # TODO: Refactor
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
        image_bytes = image_data_to_png_bytes(img_tensor)
        self._upload_artifact_at_step(
            filename=f"{tag}_{global_step}.png",  # Only needed for uploading
            content=image_bytes,
            content_type="image/png",
            name=tag,
            artifact_type="image",
            step=global_step,
            metadata={"format": "png"},
        )

    def add_text(
        self,
        tag: str,
        text_string: str,
        global_step: int = 0,
        walltime: float = 0,
    ):
        """Upload and log text as a text object."""
        self._upload_artifact_at_step(
            filename=f"{tag}_{global_step}.txt",  # Only needed for uploading
            content=text_string.encode("utf-8"),
            content_type="text/plain",
            name=tag,
            artifact_type="text",
            step=global_step,
            metadata={"encoding": "utf-8"},
        )

    # TODO: Refactor
    def log_final_artifact(
        self,
        tag: str,
        content,
        stored_filepath: str | None = None,
        default_content_type: str = "application/octet-stream",
        default_extension: str | None = None,
    ) -> None:
        """
        Upload a named final artifact without step-based logging.
        The logged artifact haven't a step associated with it, used for checkpoints, configs, final exports.
        Args:
            tag (str): The name of the artifact (displayed in the ui).
            content (bytes): The content of the artifact.
            stored_filepath (str | None): The relative filepath of the artifact in the ui.
            default_content_type (str): The default content type of the artifact.
        """
        try:
            file_name = tag
            if default_extension and not Path(file_name).suffix:
                file_name = f"{file_name}{default_extension}"
            filepath = stored_filepath or (
                f"final/{file_name}" if default_extension else file_name
            )
            resolved_default_content_type = default_content_type
            guessed_content_type, _ = mimetypes.guess_type(file_name)
            if guessed_content_type is not None:
                resolved_default_content_type = guessed_content_type
            elif isinstance(content, str):
                resolved_default_content_type = "text/plain"
            if _is_existing_file_path(content):
                file_name = Path(content).name
                filepath = str(Path(content).relative_to(Path.cwd()))

            content_bytes, _, content_type = materialize_content(
                content=content,
                default_file_name=file_name,
                default_mime_type=resolved_default_content_type,
            )

            self._blob_api.upsert_named_experiment_artifact(
                experiment_id=str(self.experiment_id),
                filepath=filepath,
                filename=file_name,
                content=content_bytes,
                content_type=content_type,
                name=tag,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"Failed to log final artifact '{tag}': {exc}", stack_info=True
            )
            raise

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
        logger.warning("add_mesh is not implemented")

    def add_video(
        self,
        tag: str,
        vid_tensor,
        global_step: int = 0,
        walltime: float = 0,
        fps: int = 4,
    ):
        """Upload and log video object."""
        logger.warning("add_video is not implemented")

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
            progress = min(max(progress, 0), 100)
        if isinstance(progress, float):
            progress = min(max(progress, 0), 1)
            progress = round(progress * 100)
        self._request_client.queued_request(
            self._api_requests_registry.experiments.update_experiment(
                self.experiment_id, progress=progress
            )
        )

    def status(self, status: ExperimentStatus):
        """Update the status of the experiment."""
        self._request_client.queued_request(
            self._api_requests_registry.experiments.update_experiment(
                self.experiment_id, status=status
            )
        )

    def tags(self, *tags: str):
        """Update the tags of the experiment."""
        self._request_client.request(
            self._api_requests_registry.experiments.update_experiment(
                self.experiment_id, tags=list(tags)
            )
        )

    def color(self, color: str):
        """Update the color of the experiment."""
        if not re.fullmatch(r"^#[0-9a-fA-F]{6}$", color):
            raise ExpTrackerAPIError(f"Invalid color: {color}")
        self._request_client.request(
            self._api_requests_registry.experiments.update_experiment(
                self.experiment_id, color=color
            )
        )

    def description(self, description: str):
        """Update the description of the experiment."""
        self._request_client.request(
            self._api_requests_registry.experiments.update_experiment(
                self.experiment_id, description=description
            )
        )

    def features(self, features: list[FeatureNodeLike]):
        """Update the feature tree for the experiment."""
        self._request_client.request(
            self._api_requests_registry.experiments.update_experiment(
                self.experiment_id, features=features
            )
        )

    def name(self, name: str):
        """Update the name of the experiment."""
        self._request_client.request(
            self._api_requests_registry.experiments.update_experiment(
                self.experiment_id, name=name
            )
        )

    def parent_experiment(self, parent_experiment: str | UUID):
        """Update the parent experiment of the experiment."""
        experiments = cast(
            ExperimentListResponse,
            self._request_client.request(
                self._api_requests_registry.experiments.get_experiments_by_project(
                    self.project_id
                )
            ),
        ).data
        # TODO: Must be paginated in the future
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
        self._request_client.request(
            self._api_requests_registry.experiments.update_experiment(
                self.experiment_id, parent_experiment_id=parent_experiment_obj.id
            )
        )

    def flush(self):
        """Flush the event file to disk/network."""
        self._scalar_logging.flush()
        self._request_client.flush()

    def close(self):
        """Close the logger and free resources."""
        self._scalar_logging.flush()
        self._request_client.flush()
        self._request_client.close()
