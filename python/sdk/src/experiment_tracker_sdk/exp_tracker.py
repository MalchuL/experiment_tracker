from uuid import UUID

from experiment_tracker_sdk.logger import logger
from experiment_tracker_sdk.client import API, ExperimentStatus, ExperimentTrackerClient
from experiment_tracker_sdk.config import load_config
from experiment_tracker_sdk.error import ExpTrackerAPIError, ExpTrackerProgressError


class ExpTracker:
    """
    Minimal TensorBoard-like logging API.
    Methods mirror typical tensorboard.SummaryWriter calls:
        - add_scalar
        - add_scalars
        - add_image
        - add_images
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
        projects = api.projects.get_all_projects()
        project_obj = next(
            (p for p in projects if p.name == project or p.id == project), None
        )
        if project_obj is None:
            raise ExpTrackerAPIError(f"Project not found: {project}")
        logger.info(f"Using project: {project_obj.id} with name {project_obj.name}")
        experiment_obj = None
        if try_existing_experiment:
            # Try to find an existing experiment with the given name or ID
            experiments = api.experiments.get_experiments_by_project(project_obj.id)
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
            experiment_obj = api.experiments.create_experiment(
                project_obj.id, experiment
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
                self._api.scalars.log_scalar(
                    self.experiment_id, self._current_values, self._last_logged_step
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
        dataformats: str = "CHW",
    ):
        """Log a single image."""
        pass

    def add_images(
        self,
        tag: str,
        img_tensor,
        global_step: int = 0,
        walltime: float = 0,
        dataformats: str = "NCHW",
    ):
        """Log a batch of images."""
        pass

    def add_text(
        self,
        tag: str,
        text_string: str,
        global_step: int = 0,
        walltime: float = 0,
    ):
        """Log (markdown) text."""
        pass

    def add_histogram(
        self,
        tag: str,
        values,
        global_step: int = 0,
        bins: int = 10,
        walltime: float = 0,
    ):
        """Log a histogram of values."""
        pass

    def add_audio(
        self,
        tag: str,
        snd_tensor,
        global_step: int = 0,
        sample_rate: int = 44100,
        walltime: float = 0,
    ):
        """Log audio data."""
        pass

    def add_figure(
        self,
        tag: str,
        figure,
        global_step: int = 0,
        close: bool = True,
        walltime: float = 0,
    ):
        """Log a matplotlib figure."""
        pass

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
        """Log a 3D mesh."""
        pass

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
        pass

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
        self._api.experiments.update_experiment(self.experiment_id, progress=progress)

    def status(self, status: ExperimentStatus):
        """Update the status of the experiment."""
        self._api.experiments.update_experiment(self.experiment_id, status=status)

    def tags(self, *tags: str):
        """Update the tags of the experiment."""
        self._api.experiments.update_experiment(self.experiment_id, tags=list(tags))

    def parent_experiment(self, parent_experiment: str | UUID):
        """Update the parent experiment of the experiment."""
        experiments = self._api.experiments.get_experiments_by_project(self.project_id)
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
        self._api.experiments.update_experiment(
            self.experiment_id, parent_experiment_id=parent_experiment_obj.id
        )

    def flush(self):
        """Flush the event file to disk/network."""
        if self._current_values:
            self._api.scalars.log_scalar(
                self.experiment_id, self._current_values, self._last_logged_step
            )
            self._last_logged_step = 0
            self._current_values = {}
        self._api.flush()

    def close(self):
        """Close the logger and free resources."""
        if self._current_values:
            self._api.scalars.log_scalar(
                self.experiment_id, self._current_values, self._last_logged_step
            )
            self._last_logged_step = 0
            self._current_values = {}
        self._api.close()
