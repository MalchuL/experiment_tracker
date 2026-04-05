from experiment_tracker_sdk.client.client import ExperimentTrackerClient

class BlobAPI:
    # TODO: Implement this.
    
    def __init__(self, tracker_client: ExperimentTrackerClient):
        self._tracker_client = tracker_client

     def upload_project_artifact(
        self,
        project_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """Upload into project CAS if hash is missing."""

        from experiment_tracker_shared import compute_sha256_hexdigest

        artifact_hash = compute_sha256_hexdigest(file_content)
        check_result = self.check_project_artifacts(project_id, [artifact_hash])
        missing = set(check_result.get("missing", []))
        if artifact_hash not in missing:
            return {"status": "exists", "hash": artifact_hash}
        upload_spec = self.project_artifacts.upload_project_artifact(
            project_id, artifact_hash
        )
        upload_result = self._tracker_client.upload_file(
            path=upload_spec.endpoint,
            params=upload_spec.query_params or {},
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
        )
        return {"status": "uploaded", "hash": artifact_hash, "upload": upload_result}

    def upload_and_log_experiment_artifact_at_step(
        self,
        experiment_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Upload file to experiment bucket and log metadata in one call.

        Uses experiment-scoped storage (no deduplication). For deduplicated
        project CAS, use upload_and_log_artifact instead.
        """
        import json

        request_model = LogArtifactAtStepRequest(
            name=name,
            artifact_type=cast(ArtifactType, artifact_type),
            step=step,
            metadata=metadata,
            tags=tags,
        )
        upload_spec = (
            self.experiment_artifacts.upload_and_log_experiment_artifact_at_step(
                experiment_id=experiment_id,
                request=request_model,
            )
        )
        request_payload = request_model.model_dump(exclude_none=True)
        form_data: dict[str, Any] = {
            "name": cast(str, request_payload["name"]),
            "artifact_type": cast(str, request_payload["artifact_type"]),
            "step": str(request_payload["step"]),
        }
        if "metadata" in request_payload:
            form_data["metadata"] = json.dumps(request_payload["metadata"])
        if "tags" in request_payload:
            form_data["tags"] = json.dumps(request_payload["tags"])
        return self._tracker_client.upload_artifact(
            path=upload_spec.endpoint,
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
            form_data=form_data,
        )

    def upsert_named_experiment_artifact(
        self,
        experiment_id: str,
        name: str,
        filepath: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """Upsert named final artifact for an experiment."""
        upload_spec = self.experiment_artifacts.upsert_named_experiment_artifact(
            experiment_id=experiment_id,
            name=name,
            filepath=filepath,
        )
        form_data = {
            "experiment_id": experiment_id,
            "name": name,
            "filepath": filepath,
        }
        return self._tracker_client.upload_artifact(
            path=upload_spec.endpoint,
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
            form_data=form_data,
        )

    def download_project_artifact(self, project_id: str, artifact_hash: str) -> bytes:
        """Download project artifact bytes by hash (project-scoped CAS)."""
        request_spec = self.project_artifacts.download_project_artifact(
            project_id=project_id,
            artifact_hash=artifact_hash,
        )
        return self._tracker_client.download_file(
            path=request_spec.endpoint,
            params=request_spec.query_params,
        )

    def download_experiment_artifact_at_step(
        self,
        experiment_id: str,
        step: int,
        name: str,
        artifact_type: str | None = None,
    ) -> bytes:
        """Download artifact bytes for a logged step/name (resolved via scalars)."""
        request_spec = self.experiment_artifacts.download_experiment_artifact_at_step(
            experiment_id=experiment_id,
            step=step,
            name=name,
            artifact_type=artifact_type,
        )
        return self._tracker_client.download_file(
            path=request_spec.endpoint,
            params=request_spec.query_params,
        )

    # Backward-compatible wrappers.
    def upload_and_log_experiment_artifact(
        self,
        experiment_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.upload_and_log_experiment_artifact_at_step(
            experiment_id=experiment_id,
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
            name=name,
            artifact_type=artifact_type,
            step=step,
            metadata=metadata,
            tags=tags,
        )

    def download_experiment_artifact(
        self,
        experiment_id: str,
        step: int,
        name: str,
        artifact_type: str | None = None,
    ) -> bytes:
        return self.download_experiment_artifact_at_step(
            experiment_id=experiment_id,
            step=step,
            name=name,
            artifact_type=artifact_type,
        )

    def download_project_artifact_to_file(
        self, project_id: str, artifact_hash: str, output_path: str | Path
    ) -> Path:
        """Download project artifact and write it to a local file path."""
        request_spec = self.project_artifacts.download_project_artifact(
            project_id=project_id,
            artifact_hash=artifact_hash,
        )
        return self._tracker_client.download_file_to_path(
            path=request_spec.endpoint,
            output_path=output_path,
            params=request_spec.query_params,
        )