from __future__ import annotations

from uuid import UUID

from experiment_tracker_sdk.client.request_types import ApiRequestSpec

from .dto import (
    ExperimentHparamsResponse,
    ExperimentHparamsUpsertRequest,
    ExperimentSnapshotResponse,
    ExperimentSnapshotUpsertRequest,
    SnapshotFileEntry,
)


class ExperimentDataRequestSpecFactory:
    """Build SDK request specifications for experiment-data endpoints.

    Args:
        None. The factory is stateless and uses ``BASE_ENDPOINT`` for route
        construction.

    Result:
        Request-spec builder used by ``APIRequestsRegistry.experiment_data``.
    """

    BASE_ENDPOINT = "/experiments"

    def upsert_snapshot(
        self,
        experiment_id: str | UUID,
        files: list[SnapshotFileEntry],
    ) -> ApiRequestSpec[ExperimentSnapshotResponse]:
        """Build the request spec for creating or replacing a snapshot manifest.

        Args:
            experiment_id: Experiment UUID or string identifier.
            files: Manifest entries containing snapshot paths and hashes.

        Returns:
            ``ApiRequestSpec`` for ``POST /experiments/{id}/data/snapshot`` with
            the expected response model.
        """
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        return ApiRequestSpec(
            method="POST",
            endpoint=f"{self.BASE_ENDPOINT}/{experiment_id}/data/snapshot",
            request_payload=ExperimentSnapshotUpsertRequest(files=files),
            response_model=ExperimentSnapshotResponse,
        )

    def upsert_hparams(
        self,
        experiment_id: str | UUID,
        hparams: dict[str, object],
    ) -> ApiRequestSpec[ExperimentHparamsResponse]:
        """Build a complete hparams replacement request."""

        return ApiRequestSpec(
            method="PUT",
            endpoint=f"{self.BASE_ENDPOINT}/{experiment_id}/hparams",
            request_payload=ExperimentHparamsUpsertRequest(hparams=hparams),
            response_model=ExperimentHparamsResponse,
        )


ExperimentDataService = ExperimentDataRequestSpecFactory
