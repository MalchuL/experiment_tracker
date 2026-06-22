import json
import math
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from experiment_tracker_sdk.client import (
    ExperimentStatus,
    ExperimentTrackerClient,
)
from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.artifact_client import ArtifactClient
from experiment_tracker_sdk.client.domain.experiment_artifacts.dto import ArtifactType
from experiment_tracker_sdk.client.domain.experiments.dto import (
    ExperimentResponse,
    FeatureNodeLike,
)
from experiment_tracker_sdk.client.fetching_domain_pages import (
    fetch_all_project_experiments,
)
from experiment_tracker_sdk.client.instances import ExperimentInstance
from experiment_tracker_sdk.client.scalar_batching_strategy import (
    BatchedScalarLoggingStrategy,
)
from experiment_tracker_sdk.error import ExpTrackerAPIError
from experiment_tracker_sdk.hparams import serialize_hparams
from experiment_tracker_sdk.logger import logger
from experiment_tracker_sdk.settings import get_exp_tracker_settings
from experiment_tracker_sdk.snapshot import (
    DEFAULT_IGNORE_FILES,
    IgnoreFileInput,
    SnapshotPathInput,
    SnapshotRootInput,
    SnapshotUploader,
    SnapshotUploadResult,
    normalize_snapshot_max_file_size,
)
from experiment_tracker_sdk.utils.chart import (
    ChartLabelInput,
    ChartLayoutConfig,
    ChartNumericInput,
    ChartVertexInput,
    chart_artifact_filename,
    encode_chart_payload,
    extract_scatter3d_vertices,
    finite_float_values,
    finite_pie_slices,
    finite_scatter_xy,
    histogram_preview,
    require_equal_lengths,
    sample_xy_evenly,
)
from experiment_tracker_sdk.utils.chart.tensor_values import (
    flatten_numeric_values,
    numeric_sequence_length,
    vertex_row_count,
)
from experiment_tracker_sdk.utils.content_utils import (
    FinalArtifactContent,
    ImageContent,
    ImageDataContent,
    StructuredFinalArtifactContent,
    prepare_final_artifact_content,
    prepare_final_image_content,
    prepare_final_json_content,
    prepare_final_yaml_content,
    prepare_step_image_content,
    prepare_step_text_content,
)
from experiment_tracker_sdk.utils.experiment_init_strategy import (
    ExperimentInitStrategy,
    InitParams,
)
from experiment_tracker_sdk.utils.color_utils import random_hex_color

_SNAPSHOT_MAX_FILE_SIZE_UNSET = object()


class ExpTracker:
    """TensorBoard-style experiment logger for the Experiment Tracker API.

    Binds to one experiment and exposes convenience methods for logging
    scalars, metrics, step artifacts (images, text, charts), final artifacts,
    code snapshots, and experiment metadata. Method names mirror
    ``tensorboard.SummaryWriter`` where applicable (``add_scalar``,
    ``add_image``, ``flush``, ``close``, and similar).

    Prefer :meth:`init` when resolving team, project, and experiment objects
    from names or ids. Use the constructor when you already hold ids and SDK
    client handles.

    Metadata helpers such as :meth:`status`, :meth:`progress`, :meth:`name`,
    and :meth:`tags` mutate the bound
    :class:`~experiment_tracker_sdk.client.instances.ExperimentInstance`.
    Outside a ``with tracker:`` block each assignment triggers an API update;
    inside the context manager updates are batched and sent on clean exit.

    Scalar batches and queued HTTP requests are flushed by :meth:`flush` and
    :meth:`close`. Call :meth:`close` at the end of a training run.

    Attributes:
        experiment_id: Experiment UUID bound to this tracker.
        project_id: Owning project UUID.
    """

    def __init__(
        self,
        experiment_id: str | UUID,
        project_id: str | UUID,
        api_requests_registry: APIRequestsRegistry,
        request_client: ExperimentTrackerClient,
        experiment_instance: ExperimentInstance | None = None,
        *,
        verbose: bool = False,
    ):
        """Initialize an ``ExpTracker`` bound to an existing experiment.

        Args:
            experiment_id: Experiment UUID or string id bound to this tracker.
            project_id: Project UUID or string id that owns the experiment.
            api_requests_registry: Registry of API request spec factories used to
                build endpoint calls.
            request_client: HTTP client used for API calls and artifact uploads.
            experiment_instance: Optional pre-built experiment handle. When
                omitted, a minimal placeholder instance is created from
                ``experiment_id`` and ``project_id``.
            verbose: When ``True``, show tqdm progress bars during artifact
                uploads (images, text, final artifacts, snapshots, and similar).

        Returns:
            None.
        """
        self.experiment_id = experiment_id
        self.project_id = project_id
        self._api_requests_registry = api_requests_registry
        self._request_client = request_client
        self._verbose = verbose
        self._artifacts = ArtifactClient(
            registry=api_requests_registry,
            request_client=request_client,
        )
        self._scalar_logging = BatchedScalarLoggingStrategy(
            experiment_id=experiment_id,
            registry=api_requests_registry,
            request_client=request_client,
        )
        self._experiment = experiment_instance or ExperimentInstance._from_response(
            ExperimentResponse(
                id=str(experiment_id),
                projectId=str(project_id),
                name="",
                description="",
                status=ExperimentStatus.PLANNED.value,
                createdAt=datetime.now(),
            ),
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )

    def __enter__(self) -> "ExpTracker":
        """Enter batched experiment metadata update mode.

        While inside the context, property updates on the bound experiment
        instance (``status``, ``progress``, ``name``, and similar) are queued
        and sent in one API call on clean exit.

        Returns:
            This tracker instance.
        """
        self._experiment.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[exit-return]
        """Leave batched experiment metadata update mode.

        Args:
            exc_type: Exception type raised inside the context, or ``None`` on a
                clean exit.
            exc: Exception instance raised inside the context, or ``None``.
            tb: Traceback for the exception raised inside the context, or
                ``None``.

        Returns:
            ``False`` so exceptions are never suppressed.
        """
        return self._experiment.__exit__(exc_type, exc, tb)

    def _resolve_verbose(self, verbose: bool | None) -> bool:
        """Resolve per-call verbosity against the tracker default.

        Args:
            verbose: Per-call override. ``None`` falls back to the tracker-level
                ``verbose`` flag from construction or :meth:`init`.

        Returns:
            Effective verbosity flag for artifact uploads.
        """
        if verbose is not None:
            return verbose
        return self._verbose

    def get_project_settings(self) -> dict[str, Any]:
        """Fetch runtime project settings as a name-to-value mapping.

        Returns:
            Project settings dictionary keyed by setting name.

        Raises:
            ExpTrackerAPIError: If the API response is not a dictionary.
        """
        response = self._request_client.request(
            self._api_requests_registry.projects.get_project_settings_map(
                self.project_id
            )
        )
        if not isinstance(response, dict):
            raise ExpTrackerAPIError(
                "Unexpected project settings response: expected a dictionary"
            )
        return dict(response)

    @classmethod
    def init(
        cls,
        project: str | UUID,
        experiment: str | UUID,
        team: str | UUID | None = None,
        init_params: InitParams | None = None,
        *,
        verbose: bool = False,
    ) -> "ExpTracker":
        """Create and configure an ``ExpTracker`` for a project experiment.

        Resolves or creates team, project, and experiment objects according to
        ``init_params``, then assigns a random hex color to the experiment.

        Args:
            project: Project id or name to resolve.
            experiment: Experiment id or name to resolve inside the project.
            team: Optional team id or name used to resolve team-owned projects
                and to create a team/project when requested by ``init_params``.
            init_params: Initialization behavior. Controls whether existing
                team/project/experiment objects are reused, how ambiguous
                matches are resolved, and whether missing objects are created.
                When omitted, missing experiments are created by default while
                projects and teams must already exist.
            verbose: When ``True``, show tqdm progress bars during artifact
                uploads performed through the returned tracker.

        Returns:
            Configured ``ExpTracker`` bound to the resolved experiment.

        Raises:
            ExperimentInitError: When team, project, or experiment resolution
                fails (not found, ambiguous match, or policy violation).
            ExpTrackerAPIError: When an underlying API request fails.
        """
        resolved_init_params = init_params or InitParams(
            create_experiment_if_not_exists=True,
        )
        strategy = ExperimentInitStrategy()
        result = strategy.init(
            experiment_name_or_id=experiment,
            project_name_or_id=project,
            team_name_or_id=team,
            init_params=resolved_init_params,
        )
        tracker = cls(
            result.experiment.id,
            result.project.id,
            strategy.api_requests_registry,
            strategy.request_client,
            experiment_instance=result.experiment,
            verbose=verbose,
        )
        tracker.color(random_hex_color())
        return tracker

    def add_scalar(
        self, tag: str, scalar_value, global_step: int = 0, walltime: float = 0
    ):
        """Log a single scalar value at a training step.

        Values are buffered and sent in batches; call :meth:`flush` or
        :meth:`close` to force delivery. Non-numeric inputs are ignored with a
        warning. ``NaN`` and ``±inf`` are accepted and forwarded to the API.

        Args:
            tag: Scalar series name shown in the UI.
            scalar_value: Numeric value to log.
            global_step: Training step index.
            walltime: Unused; kept for TensorBoard API compatibility.

        Returns:
            None.
        """
        _ = walltime  # Kept for API parity with TensorBoard-style signatures.
        if not isinstance(scalar_value, (int, float)):
            logger.warning(
                f"Invalid scalar value: {scalar_value} for tag: {tag}, "
                f"global_step: {global_step}, not logged"
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
        """Log multiple scalar values under one step.

        Each key in ``tag_scalar_dict`` is concatenated with ``main_tag`` and
        logged via :meth:`add_scalar`.

        Args:
            main_tag: Prefix prepended to every key in ``tag_scalar_dict``.
            tag_scalar_dict: Mapping of suffix tag to scalar value.
            global_step: Training step index shared by all logged scalars.
            walltime: Unused; kept for TensorBoard API compatibility.

        Returns:
            None.
        """
        for tag, scalar_value in tag_scalar_dict.items():
            self.add_scalar(main_tag + tag, scalar_value, global_step, walltime)

    def add_metric(
        self,
        name: str,
        value: float,
        label: str | None = None,
        walltime: float = 0,
    ):
        """Create or update a project metric row for this experiment.

        Metrics are keyed by ``(name, label)`` and are distinct from step
        scalars. Non-finite values are ignored with a warning.

        Args:
            name: Metric name.
            value: Metric value (must be finite).
            label: Optional metric label distinguishing multiple values with
                the same name.
            walltime: Unused; kept for TensorBoard API compatibility.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When the metrics upsert API call fails.
        """
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

    def add_image(
        self,
        tag: str,
        img: ImageDataContent,
        global_step: int = 0,
        walltime: float = 0,
        verbose: bool | None = None,
    ):
        """Upload and log a single image at a training step.

        Supported inputs:
            - ``PIL.Image.Image``
            - ``numpy.ndarray`` in HW or HWC layout
            - ``torch.Tensor`` in CHW, HW, or HWC layout

        Images are converted to PNG and stored as step-based logged objects.

        Args:
            tag: Logical name shown in the UI.
            img: Image payload in one of the supported formats above.
            global_step: Training step index.
            walltime: Unused; kept for TensorBoard API compatibility.
            verbose: Upload progress bar for this call only. ``None`` uses the
                tracker-level ``verbose`` from construction or :meth:`init`.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When optional image dependencies are missing,
                the input shape is unsupported, or the upload API call fails.
        """
        prepared = prepare_step_image_content(tag, img, global_step)
        self._artifacts.upload_and_log_experiment_artifact_at_step(
            experiment_id=str(self.experiment_id),
            filename=prepared.filename,
            content=prepared.content,
            content_type=prepared.content_type,
            name=tag,
            artifact_type="image",
            step=global_step,
            metadata={"format": "png"},
            verbose=self._resolve_verbose(verbose),
        )

    def add_text(
        self,
        tag: str,
        text_string: str,
        global_step: int = 0,
        walltime: float = 0,
        verbose: bool | None = None,
    ):
        """Upload and log UTF-8 text at a training step.

        Args:
            tag: Logical name shown in the UI.
            text_string: Text content to store.
            global_step: Training step index.
            walltime: Unused; kept for TensorBoard API compatibility.
            verbose: Upload progress bar for this call only. ``None`` uses the
                tracker-level ``verbose`` from construction or :meth:`init`.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When the upload API call fails.
        """
        prepared = prepare_step_text_content(tag, text_string, global_step)
        self._artifacts.upload_and_log_experiment_artifact_at_step(
            experiment_id=str(self.experiment_id),
            filename=prepared.filename,
            content=prepared.content,
            content_type=prepared.content_type,
            name=tag,
            artifact_type="text",
            step=global_step,
            metadata={"encoding": "utf-8"},
            verbose=self._resolve_verbose(verbose),
        )

    def _upload_chart_artifact_at_step(
        self,
        *,
        tag: str,
        artifact_type: ArtifactType,
        global_step: int,
        data: list[dict],
        layout: dict | None,
        metadata: dict[str, str],
    ) -> None:
        """Upload a chart JSON artifact for the current experiment step.

        Args:
            tag: Logical name shown in the UI.
            artifact_type: Logged object type (histogram, scatter, pie, etc.).
            global_step: Training step index.
            data: Serialized trace payloads for the chart renderer.
            layout: Optional chart layout dict merged into the payload.
            metadata: String key/value metadata stored alongside the artifact.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When the upload API call fails.
        """
        self._artifacts.upload_and_log_experiment_artifact_at_step(
            experiment_id=str(self.experiment_id),
            filename=chart_artifact_filename(tag, global_step),
            content=encode_chart_payload(data, layout),
            content_type="application/json",
            name=tag,
            artifact_type=artifact_type,
            step=global_step,
            metadata=metadata,
            verbose=self._resolve_verbose(None),
        )

    def log_final_artifact(
        self,
        tag: str,
        content: FinalArtifactContent,
        stored_filepath: str | None = None,
        default_content_type: str = "application/octet-stream",
        default_extension: str | None = None,
        verbose: bool | None = None,
    ) -> None:
        """Upload a named final artifact without step-based logging.

        Final artifacts are tracked experiment blobs with a stable name and
        filepath but no ``global_step``. Use for checkpoints, configs, final
        exports, and other run outputs that do not need a typed convenience
        helper.

        Args:
            tag: Logical artifact name displayed in the UI.
            content: Bytes, text, an existing file path, or a readable file-like
                object. Existing paths are read from disk; strings that are not
                paths are uploaded as UTF-8 text.
            stored_filepath: Relative filepath to store/display in the UI. When
                omitted, a path is derived from ``tag`` and ``default_extension``.
            default_content_type: MIME type used when it cannot be inferred from
                a file name.
            default_extension: Extension appended to ``tag`` when building the
                default stored path and multipart filename.
            verbose: Upload progress bar for this call only. ``None`` uses the
                tracker-level ``verbose`` from construction or :meth:`init`.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When content preparation or the upload API call
                fails. Errors are logged before re-raising.
        """
        try:
            prepared = prepare_final_artifact_content(
                tag=tag,
                content=content,
                stored_filepath=stored_filepath,
                default_content_type=default_content_type,
                default_extension=default_extension,
            )

            self._artifacts.upsert_named_experiment_artifact(
                experiment_id=str(self.experiment_id),
                filepath=prepared.filepath,
                filename=prepared.filename,
                content=prepared.content,
                content_type=prepared.content_type,
                name=tag,
                verbose=self._resolve_verbose(verbose),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"Failed to log final artifact '{tag}': {exc}", stack_info=True
            )
            raise

    def log_final_image(
        self,
        tag: str,
        content: ImageContent,
        stored_filepath: str | None = None,
        verbose: bool | None = None,
    ) -> None:
        """Upload a named final image artifact without step-based logging.

        Bytes, paths, and readable file-like objects are uploaded directly.
        Other values are treated like :meth:`add_image` input and converted to
        PNG bytes; this supports PIL images and numpy arrays when those
        optional packages are installed.

        Args:
            tag: Logical artifact name displayed in the UI.
            content: Image bytes, an existing image file path, a readable
                file-like object, a PIL image, or a numpy array in HW/HWC
                layout.
            stored_filepath: Relative filepath to store/display in the UI.
            verbose: Passed through to :meth:`log_final_artifact`.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When image conversion or upload fails.
        """
        self.log_final_artifact(
            tag,
            prepare_final_image_content(content),
            stored_filepath=stored_filepath,
            default_content_type="image/png",
            default_extension=".png",
            verbose=verbose,
        )

    def log_final_text(
        self,
        tag: str,
        content: FinalArtifactContent,
        stored_filepath: str | None = None,
        verbose: bool | None = None,
    ) -> None:
        """Upload a named final text artifact without step-based logging.

        Args:
            tag: Logical artifact name displayed in the UI.
            content: Text, bytes, an existing text file path, or a readable
                file-like object. Text strings that are not paths are encoded as
                UTF-8 by the generic upload path.
            stored_filepath: Relative filepath to store/display in the UI.
            verbose: Passed through to :meth:`log_final_artifact`.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When content preparation or upload fails.
        """
        self.log_final_artifact(
            tag,
            content,
            stored_filepath=stored_filepath,
            default_content_type="text/plain",
            default_extension=".txt",
            verbose=verbose,
        )

    def log_final_json(
        self,
        tag: str,
        content: StructuredFinalArtifactContent,
        stored_filepath: str | None = None,
        indent: int | None = 2,
        verbose: bool | None = None,
    ) -> None:
        """Upload a named final JSON artifact without step-based logging.

        Args:
            tag: Logical artifact name displayed in the UI.
            content: JSON text, bytes, an existing JSON file path, a readable
                file-like object, or a structured mapping/list payload. Structured
                payloads are serialized with ``json.dumps``.
            stored_filepath: Relative filepath to store/display in the UI.
            indent: Indentation passed to ``json.dumps`` for structured payloads.
            verbose: Passed through to :meth:`log_final_artifact`.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When content preparation or upload fails.
        """
        self.log_final_artifact(
            tag,
            prepare_final_json_content(content, indent=indent),
            stored_filepath=stored_filepath,
            default_content_type="application/json",
            default_extension=".json",
            verbose=verbose,
        )

    def log_final_yaml(
        self,
        tag: str,
        content: StructuredFinalArtifactContent,
        stored_filepath: str | None = None,
        verbose: bool | None = None,
    ) -> None:
        """Upload a named final YAML artifact without step-based logging.

        Args:
            tag: Logical artifact name displayed in the UI.
            content: YAML text, bytes, an existing YAML file path, a readable
                file-like object, or a structured mapping/list payload. Structured
                payloads are serialized with the SDK's lightweight YAML emitter.
            stored_filepath: Relative filepath to store/display in the UI.
            verbose: Passed through to :meth:`log_final_artifact`.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When content preparation or upload fails.
        """
        self.log_final_artifact(
            tag,
            prepare_final_yaml_content(content),
            stored_filepath=stored_filepath,
            default_content_type="application/x-yaml",
            default_extension=".yaml",
            verbose=verbose,
        )

    def log_snapshot(
        self,
        path: SnapshotPathInput = ".",
        *,
        root: SnapshotRootInput = None,
        ignore_file: IgnoreFileInput = DEFAULT_IGNORE_FILES,
        max_file_size: int | None | object = _SNAPSHOT_MAX_FILE_SIZE_UNSET,
        verbose: bool | None = None,
    ) -> SnapshotUploadResult:
        """Upload a content-addressed code snapshot for this experiment.

        Scans local files, uploads missing blobs to project storage, and
        registers a snapshot manifest on the experiment. Ignore rules follow
        ``.gitignore`` and ``.exp_trackerignore`` by default.

        Args:
            path: File, directory, or iterable of paths to include. Defaults to
                the current directory (``"."``).
            root: Absolute directory used for manifest-relative paths, or
                ``None`` to discover one from ignore files.
            ignore_file: Ignore-file name or names applied during scanning.
            max_file_size: Maximum included file size in bytes. When omitted,
                uses ``EXP_TRACKER_SNAPSHOT_MAX_FILE_SIZE`` from settings.
                ``None`` or a negative value disables size filtering.
            verbose: Upload progress bar for this call only. ``None`` uses the
                tracker-level ``verbose`` from construction or :meth:`init`.

        Returns:
            :class:`~experiment_tracker_sdk.snapshot.SnapshotUploadResult`
            summarizing included, skipped, uploaded, and deduplicated files.

        Raises:
            ExpTrackerAPIError: When scanning, hashing, or upload fails.
            ValueError: When ``root`` or ignore-file paths are invalid.
        """
        resolved_max_file_size = (
            get_exp_tracker_settings().snapshot_max_file_size
            if max_file_size is _SNAPSHOT_MAX_FILE_SIZE_UNSET
            else normalize_snapshot_max_file_size(cast(int | None, max_file_size))
        )
        uploader = SnapshotUploader(
            registry=self._api_requests_registry,
            request_client=self._request_client,
        )
        return uploader.log_snapshot(
            project_id=str(self.project_id),
            experiment_id=str(self.experiment_id),
            path=path,
            root=root,
            ignore_file=ignore_file,
            max_file_size=resolved_max_file_size,
            verbose=self._resolve_verbose(verbose),
        )

    def add_histogram(
        self,
        tag: str,
        values: ChartNumericInput,
        global_step: int = 0,
        bins: int | None = None,
        walltime: float = 0,
    ) -> None:
        """Log a histogram of numeric values as a step chart artifact.

        Args:
            tag: Logical name shown in the UI.
            values: Samples as a sequence, numpy array, or torch tensor. Two-
                dimensional and higher arrays are flattened.
            global_step: Training step index.
            bins: Histogram bin count for the trace and preview metadata. Uses
                ``histogram_metadata_bins`` from settings when omitted.
            walltime: Unused; kept for TensorBoard API compatibility.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When the chart upload API call fails.
        """
        _ = walltime
        numeric_values = finite_float_values(values)
        metadata_bins = bins or get_exp_tracker_settings().histogram_metadata_bins
        preview = histogram_preview(numeric_values, metadata_bins)
        self._upload_chart_artifact_at_step(
            tag=tag,
            artifact_type="histogram",
            global_step=global_step,
            data=[
                {
                    "type": "histogram",
                    "x": numeric_values,
                    "nbinsx": metadata_bins,
                    "name": tag,
                }
            ],
            layout={"title": {"text": tag}, "bargap": 0.05},
            metadata={
                "preview_kind": "histogram_bins",
                "preview_data": json.dumps(
                    preview, allow_nan=False, separators=(",", ":")
                ),
            },
        )

    def add_audio(
        self,
        tag: str,
        snd_tensor,
        global_step: int = 0,
        sample_rate: int = 44100,
        walltime: float = 0,
    ):
        """Log audio at a training step.

        Not implemented. Emits a warning and returns without uploading.

        Args:
            tag: Logical name that would be shown in the UI.
            snd_tensor: Audio tensor payload.
            global_step: Training step index.
            sample_rate: Audio sample rate in Hz.
            walltime: Unused; kept for TensorBoard API compatibility.

        Returns:
            None.
        """
        logger.warning("add_audio is not implemented")

    def add_figure(
        self,
        tag: str,
        figure,
        global_step: int = 0,
        close: bool = True,
        walltime: float = 0,
    ):
        """Log a matplotlib figure at a training step.

        Not implemented. Emits a warning and returns without uploading.

        Args:
            tag: Logical name that would be shown in the UI.
            figure: Matplotlib figure object.
            global_step: Training step index.
            close: Whether the figure would be closed after logging.
            walltime: Unused; kept for TensorBoard API compatibility.

        Returns:
            None.
        """
        logger.warning("add_figure is not implemented")

    def add_pie(
        self,
        tag: str,
        labels: ChartLabelInput,
        values: ChartNumericInput,
        global_step: int = 0,
        walltime: float = 0,
    ) -> None:
        """Log a pie chart (labels and slice values) at a training step.

        Args:
            tag: Logical name shown in the UI.
            labels: Slice labels (same length as ``values``).
            values: Slice sizes as a sequence, numpy array, or torch tensor.
            global_step: Training step index.
            walltime: Unused; kept for TensorBoard API compatibility.

        Returns:
            None.

        Raises:
            ValueError: If ``labels`` and ``values`` lengths differ.
            ExpTrackerAPIError: When the chart upload API call fails.
        """
        _ = walltime
        labels_list, numeric_values = finite_pie_slices(labels, values)
        total = len(labels_list)
        self._upload_chart_artifact_at_step(
            tag=tag,
            artifact_type="pie",
            global_step=global_step,
            data=[
                {
                    "type": "pie",
                    "labels": labels_list,
                    "values": numeric_values,
                    "name": tag,
                }
            ],
            layout={"title": {"text": tag}},
            metadata={"total_slices": str(total)},
        )

    def add_scatter(
        self,
        tag: str,
        x: ChartNumericInput,
        y: ChartNumericInput,
        global_step: int = 0,
        mode: str = "markers",
        walltime: float = 0,
    ) -> None:
        """Log a 2D scatter chart at a training step.

        Args:
            tag: Logical name shown in the UI.
            x: X coordinates as a sequence, numpy array, or torch tensor.
            y: Y coordinates (same length as ``x`` after flattening).
            global_step: Training step index.
            mode: Plotly trace mode (for example ``"markers"`` or ``"lines"``).
            walltime: Unused; kept for TensorBoard API compatibility.

        Returns:
            None.

        Raises:
            ValueError: If ``x`` and ``y`` lengths differ.
            ExpTrackerAPIError: When the chart upload API call fails.
        """
        _ = walltime
        x_values, y_values = finite_scatter_xy(x, y)
        total = len(x_values)
        max_points = get_exp_tracker_settings().scatter_metadata_max_points
        preview_x, preview_y = sample_xy_evenly(x_values, y_values, max_points)
        preview = {
            "x": preview_x,
            "y": preview_y,
            "total": total,
            "sampled": len(preview_x),
        }
        self._upload_chart_artifact_at_step(
            tag=tag,
            artifact_type="scatter",
            global_step=global_step,
            data=[
                {
                    "type": "scatter",
                    "mode": mode,
                    "x": x_values,
                    "y": y_values,
                    "name": tag,
                }
            ],
            layout={"title": {"text": tag}},
            metadata={
                "preview_kind": "scatter_points",
                "preview_data": json.dumps(
                    preview, allow_nan=False, separators=(",", ":")
                ),
            },
        )

    def add_mesh(
        self,
        tag: str,
        vertices: ChartVertexInput,
        colors: ChartNumericInput | None = None,
        faces: Any | None = None,
        config_dict: ChartLayoutConfig = None,
        global_step: int = 0,
        walltime: float = 0,
    ) -> None:
        """Log a 3D point cloud (scatter3d trace) at a training step.

        Args:
            tag: Logical name shown in the UI.
            vertices: Points as ``(N, 3)`` arrays or sequences of ``(x, y, z)``.
            colors: Optional per-point colors (same length as ``vertices``).
            faces: Unused; reserved for future mesh support.
            config_dict: Optional layout dict passed to the chart payload.
            global_step: Training step index.
            walltime: Unused; kept for TensorBoard API compatibility.

        Returns:
            None.

        Raises:
            ValueError: If ``colors`` is set and its length differs from
                ``vertices``.
            ExpTrackerAPIError: When the chart upload API call fails.
        """
        _ = walltime, faces
        xs, ys, zs = extract_scatter3d_vertices(vertices)
        trace: dict = {
            "type": "scatter3d",
            "mode": "markers",
            "x": xs,
            "y": ys,
            "z": zs,
            "name": tag,
        }
        if colors is not None:
            require_equal_lengths(
                vertices,
                colors,
                left_name="vertices",
                right_name="colors",
                left_length=vertex_row_count,
                right_length=numeric_sequence_length,
            )
            trace["marker"] = {"color": list(flatten_numeric_values(colors))}
        self._upload_chart_artifact_at_step(
            tag=tag,
            artifact_type="point_cloud_3d",
            global_step=global_step,
            data=[trace],
            layout=dict(config_dict) if config_dict else {"title": {"text": tag}},
            metadata={"total_points": str(len(xs))},
        )

    def add_video(
        self,
        tag: str,
        vid_tensor,
        global_step: int = 0,
        walltime: float = 0,
        fps: int = 4,
    ):
        """Log video at a training step.

        Not implemented. Emits a warning and returns without uploading.

        Args:
            tag: Logical name that would be shown in the UI.
            vid_tensor: Video tensor payload.
            global_step: Training step index.
            walltime: Unused; kept for TensorBoard API compatibility.
            fps: Frames per second for the encoded video.

        Returns:
            None.
        """
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
        """Log embedding projections at a training step.

        Not implemented. Emits a warning and returns without uploading.

        Args:
            mat: Embedding matrix payload.
            metadata: Optional per-row metadata.
            label_img: Optional label images.
            global_step: Training step index.
            tag: Logical name that would be shown in the UI.
            metadata_header: Optional metadata column headers.

        Returns:
            None.
        """
        _ = mat, metadata, label_img, global_step, tag, metadata_header
        logger.warning("add_embedding is not implemented")

    def progress(self, progress: int | float):
        """Update experiment completion progress.

        Integer values are clamped to ``[0, 100]``. Float values are treated as
        fractions in ``[0, 1]``, clamped, then rounded to an integer percent
        (for example ``0.255`` becomes ``26``).

        Args:
            progress: Progress as an integer percent or fractional float.

        Returns:
            None.
        """
        if isinstance(progress, int) and (progress < 0 or progress > 100):
            progress = min(max(progress, 0), 100)
        if isinstance(progress, float):
            progress = min(max(progress, 0), 1)
            progress = round(progress * 100)
        self._experiment.progress = int(progress)

    def status(self, status: ExperimentStatus):
        """Update experiment lifecycle status.

        Args:
            status: New status value (for example ``ExperimentStatus.RUNNING``).

        Returns:
            None.
        """
        self._experiment.status = status

    def tags(self, *tags: str):
        """Replace experiment tags.

        Args:
            *tags: Tag strings to store on the experiment. Passing no values
                clears tags.

        Returns:
            None.
        """
        self._experiment.tags = list(tags)

    def color(self, color: str):
        """Update experiment display color.

        Args:
            color: Hex color string (for example ``"#3b82f6"``).

        Returns:
            None.

        Raises:
            ValueError: When ``color`` is not a valid hex color.
        """
        self._experiment.color = color

    def description(self, description: str):
        """Update experiment description text.

        Args:
            description: Free-form description shown in the UI.

        Returns:
            None.
        """
        self._experiment.description = description

    def features(self, features: list[FeatureNodeLike]):
        """Replace the experiment feature tree.

        Args:
            features: Root feature nodes describing model architecture or
                experiment structure.

        Returns:
            None.
        """
        self._experiment.features = features

    def log_hparams(self, hparams: dict[str, Any]) -> None:
        """Validate and fully replace this experiment's hyperparameters.

        The payload must be a strict JSON-compatible mapping. Nested structures
        are normalized before upsert.

        Args:
            hparams: Hyperparameter mapping to store.

        Returns:
            None.

        Raises:
            HparamsSerializationError: When ``hparams`` is not a dict or
                contains values that cannot be serialized.
            ExpTrackerAPIError: When the hparams upsert API call fails.
        """

        normalized = serialize_hparams(hparams)
        self._request_client.request(
            self._api_requests_registry.experiment_data.upsert_hparams(
                self.experiment_id,
                normalized,
            )
        )

    def name(self, name: str):
        """Update experiment display name.

        Args:
            name: New experiment name.

        Returns:
            None.
        """
        self._experiment.name = name

    def parent_experiment(self, parent_experiment: str | UUID):
        """Set the parent experiment by id or name.

        Looks up the parent in the current project. The match succeeds when
        either the experiment id or display name equals ``parent_experiment``.

        Args:
            parent_experiment: Parent experiment id or name within this project.

        Returns:
            None.

        Raises:
            ExpTrackerAPIError: When no matching parent experiment is found or
                the update API call fails.
        """
        experiments = fetch_all_project_experiments(
            self.project_id,
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
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
            f"Using parent experiment: {parent_experiment_obj.id} "
            f"with name {parent_experiment_obj.name}"
        )
        self._experiment.parentExperimentId = parent_experiment_obj.id

    def flush(self):
        """Flush buffered scalar batches and queued HTTP requests.

        Does not close the underlying HTTP client. Safe to call repeatedly
        during a long-running training loop.

        Returns:
            None.
        """
        self._scalar_logging.flush()
        self._request_client.flush()

    def close(self):
        """Flush pending data and close the HTTP client.

        Scalar batches are flushed before the client is closed. Errors while
        closing the client are swallowed so cleanup can proceed.

        Returns:
            None.
        """
        self._scalar_logging.flush()
        self._request_client.flush()
        try:
            self._request_client.close()
        except Exception:
            pass
