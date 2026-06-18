from typing import Any, List, Literal
from domain.projects.repository import ProjectRepository
from domain.projects.mapper import (
    CreateDTOToSchemaProps,
    ProjectMapper,
    SchemaToDTOProps,
)
from domain.projects.errors import (
    ProjectNotAccessibleError,
    ProjectPermissionError,
    ProjectTransferError,
)
from lib.db.error import DBNotFoundError
from domain.rbac.permissions import ProjectActions
from domain.rbac.service import PermissionService
from domain.rbac.wrapper import PermissionChecker
from lib.dto_converter import DtoConverter
from lib.pagination import ListOptions
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession
from domain.projects.dto import (
    ProjectCreateDTO,
    ProjectDTO,
    ProjectDeleteResponseDTO,
    ProjectListResponseDTO,
    ProjectSettingDTO,
    ProjectSettingType,
    ProjectUsageDTO,
    ProjectUsageExperimentBucketsDTO,
    ProjectUsageScalarTableDTO,
    ProjectUsageScalarsDTO,
    ProjectUsageTotalDTO,
    ProjectUpdateDTO,
    ProjectOwnerTransferDTO,
    ProjectTeamTransferDTO,
    UsageBytesCountDTO,
)
from models import Role
from domain.team.teams.repository import TeamRepository
from domain.scalars.service import NoOpScalarsService, ScalarsServiceProtocol
from clients.object_storage import ObjectStorageClientProtocol
from lib.category_cleanup_dto import (
    CategoryCleanupErrorEntryDTO,
    CategoryCleanupResponseDTO,
    CategoryCleanupResultEntryDTO,
)
from lib.deletion_outcome import (
    append_postgres_deleted,
    finalize_deletion_outcome,
    outcome_lists_from_project_teardown,
)
from domain.projects.satellite_teardown import teardown_project_for_delete

ProjectCleanupCategory = Literal[
    "projectArtifacts", "snapshots", "experimentBuckets", "scalars"
]


class ProjectService:
    """Owns project lifecycle in Postgres: CRUD, typed settings, membership helpers, and deletion.

    ``delete_project`` removes satellite data (object storage blobs, scalars tables/rows)
    before deleting the project row; see repository expunge comments for session handling.

    Deletion walks **every experiment** under the project: for each, it deletes object-storage
    artifacts and scalars ClickHouse rows, then deletes project-level buckets/CAS in object
    storage and drops per-project ClickHouse tables. This mirrors ``TeamService.delete_team``
    so team-owned projects are cleaned consistently.
    """

    def __init__(
        self,
        db: AsyncSession,
        project_repository: ProjectRepository,
        permission_service: PermissionService,
        permission_checker: PermissionChecker,
        team_repository: TeamRepository,
        scalars_service: ScalarsServiceProtocol | None = None,
        object_storage_client: ObjectStorageClientProtocol | None = None,
    ):
        self.db = db
        self.project_repository = project_repository
        self.permission_service = permission_service
        self.permission_checker = permission_checker
        self.team_repository = team_repository
        self.project_mapper = ProjectMapper()
        self.scalars_service = scalars_service or NoOpScalarsService()
        self.object_storage_client = object_storage_client

    @staticmethod
    def _is_json_compatible(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            return all(ProjectService._is_json_compatible(item) for item in value)
        if isinstance(value, dict):
            return all(
                isinstance(key, str) and ProjectService._is_json_compatible(val)
                for key, val in value.items()
            )
        return False

    @staticmethod
    def _normalize_settings(raw_settings: Any) -> list[dict[str, Any]]:
        if isinstance(raw_settings, list):
            return raw_settings
        return []

    @staticmethod
    def _validate_setting_value(
        setting_type: ProjectSettingType | str, value: Any
    ) -> None:
        if isinstance(setting_type, str):
            setting_type = ProjectSettingType(setting_type)
        if setting_type == ProjectSettingType.INT:
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError("Setting value must be int")
            return
        if setting_type == ProjectSettingType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError("Setting value must be float")
            return
        if setting_type == ProjectSettingType.STRING:
            if not isinstance(value, str):
                raise ValueError("Setting value must be string")
            return
        if setting_type == ProjectSettingType.BOOLEAN:
            if not isinstance(value, bool):
                raise ValueError("Setting value must be boolean")
            return
        if setting_type == ProjectSettingType.JSON:
            if not ProjectService._is_json_compatible(value):
                raise ValueError("Setting value must be valid json")
            return
        raise ValueError("Unknown setting type")

    async def get_accessible_project_ids(
        self, user: UserProtocol, actions: list[str] | str | None
    ) -> list[UUID_TYPE]:
        """Return project ids where the user has the requested action.

        Args:
            user: User whose access is queried.
            actions: Action or actions that must be allowed; ``None`` delegates to the
                permission service's unfiltered lookup.

        Returns:
            list[UUID_TYPE]: Project ids accessible directly or through team
            permissions.
        """
        permission_project_ids = (
            await self.permission_service.get_user_accessible_project_ids(
                user.id, actions=actions
            )
        )
        return list(permission_project_ids)

    async def create_project(
        self, user: UserProtocol, data: ProjectCreateDTO
    ) -> ProjectDTO:
        """Create a project and provision its scalars table and object-storage bucket.

        Team projects inherit ownership from the team owner; standalone projects grant
        the creator project admin permissions. If any step fails, the database
        transaction is rolled back.

        Args:
            user: User creating the project.
            data: Project create payload, optionally including ``team_id``.

        Returns:
            ProjectDTO: Created project with zero experiment and hypothesis counts.

        Raises:
            ProjectNotAccessibleError: If the user cannot create projects in the
                requested team.
            Exception: Propagates repository or scalars provisioning failures after
                rollback.
        """
        try:
            # Check if the user is allowed to create a project in the team
            if data.team_id and not await self.permission_checker.can_create_project(
                user.id, data.team_id
            ):
                raise ProjectNotAccessibleError(
                    f"You are not allowed to create a project in team {data.team_id}"
                )
            if data.team_id:
                team = await self.team_repository.get_by_id(data.team_id)
                props = CreateDTOToSchemaProps(owner_id=team.owner_id)
            else:
                props = CreateDTOToSchemaProps(owner_id=user.id)
            project_model = self.project_mapper.project_create_dto_to_schema(
                data, props
            )
            await self.project_repository.create(project_model)
            # If the project is not in a team, add the user to the project permissions
            if not data.team_id:
                await self.permission_service.add_user_to_project_permissions(
                    user.id, project_model.id, Role.ADMIN
                )
            await self.scalars_service.create_project_table(project_model.id)
            if self.object_storage_client is not None:
                await self.object_storage_client.ensure_project_bucket(project_model.id)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e
        # When creating a project, the counts are 0
        props = SchemaToDTOProps(
            experiment_count=0,
            hypothesis_count=0,
        )
        created_project_id = project_model.id
        project_model = await self.project_repository.get_project_by_id(
            created_project_id, full_load=True
        )
        return self.project_mapper.project_schema_to_dto(
            project_model,
            props,
        )

    async def update_project(
        self, user: UserProtocol, project_id: UUID_TYPE, data: ProjectUpdateDTO
    ) -> ProjectDTO:
        """Update a project with partial data from ``ProjectUpdateDTO``.

        Args:
            user: User editing the project.
            project_id: Project identifier.
            data: Partial update payload.

        Returns:
            ProjectDTO: Updated project with loaded counts and configuration.

        Raises:
            ProjectNotAccessibleError: If the project cannot be loaded.
            ProjectPermissionError: If the user cannot edit the project.
            Exception: Propagates repository errors after rollback.
        """
        try:
            # Convert DTO to update dictionary
            update_dict = self.project_mapper.project_update_dto_to_update_dict(data)
            try:
                project_model = await self.project_repository.get_by_id(project_id)
            except DBNotFoundError:
                raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
            if not await self.permission_checker.can_edit_project(user.id, project_id):
                raise ProjectPermissionError(
                    f"User {user.id} does not have permission to update project {project_id}"
                )
            # TODO: Update metrics and settings if they are provided in the update dictionary
            # Now this doesn't support for partial updates of metrics and settings (also in mapper).
            # Update the project in the repository
            updated_project = await self.project_repository.update(
                project_id, **update_dict
            )
            updated_project = await self.project_repository.get_project_by_id(
                project_id, full_load=True
            )
            await self.db.commit()
            return self.project_mapper.project_schema_to_dto(
                updated_project,
                SchemaToDTOProps(
                    experiment_count=len(updated_project.experiments),
                    hypothesis_count=len(updated_project.hypotheses),
                ),
            )
        except Exception as e:
            await self.db.rollback()
            raise e

    async def change_project_team(
        self,
        user: UserProtocol | None,
        project_id: UUID_TYPE,
        data: ProjectTeamTransferDTO,
        *,
        admin_bypass: bool = False,
    ) -> ProjectDTO:
        """Move a project to another team or make it standalone.

        Direct project permissions are preserved. Team projects inherit ownership from
        the destination team. A standalone project keeps its current owner and receives
        explicit owner permissions.

        Args:
            user: Authenticated user requesting the transfer, or ``None`` for an
                admin-key operation.
            project_id: Project identifier to transfer.
            data: Destination team and optional owner used for an ownerless detach.
            admin_bypass: Whether to bypass user RBAC checks for an admin-key request.

        Returns:
            ProjectDTO: Updated project with its resulting team and owner.

        Raises:
            ProjectNotAccessibleError: If the project does not exist.
            ProjectPermissionError: If a regular user cannot edit the project, remove
                projects from the source team, or create projects in the destination
                team.
            ProjectTransferError: If the destination team is missing or ownerless, or
                the standalone result has no active owner.
            Exception: Propagates persistence errors after rolling back the transaction.
        """
        try:
            project = await self.project_repository.get_project_by_id(
                project_id, full_load=False
            )
            if project is None:
                raise ProjectNotAccessibleError(f"Project {project_id} not accessible")

            source_team_id = project.team_id
            destination_team_id = data.team_id

            if not admin_bypass:
                if user is None or not await self.permission_checker.can_edit_project(
                    user.id, project_id
                ):
                    raise ProjectPermissionError(
                        f"User cannot change team for project {project_id}"
                    )
                if source_team_id is None:
                    if project.owner_id != user.id and not getattr(
                        user, "is_superuser", False
                    ):
                        raise ProjectPermissionError(
                            "Only the current owner can move a standalone project"
                        )
                elif not await self.permission_checker.can_delete_team_project(
                    user.id, source_team_id
                ):
                    raise ProjectPermissionError(
                        "You do not have permission to remove projects from the source team"
                    )
                if destination_team_id is not None and not await self.permission_checker.can_create_project(
                    user.id, destination_team_id
                ):
                    raise ProjectPermissionError(
                        "You do not have permission to create projects in the destination team"
                    )

            if source_team_id == destination_team_id:
                await self.db.commit()
                loaded = await self.project_repository.get_project_by_id(
                    project_id, full_load=True
                )
                return self.project_mapper.project_schema_to_dto(
                    loaded,
                    SchemaToDTOProps(
                        experiment_count=len(loaded.experiments),
                        hypothesis_count=len(loaded.hypotheses),
                    ),
                )

            if destination_team_id is not None:
                try:
                    destination_team = await self.team_repository.get_by_id(
                        destination_team_id
                    )
                except DBNotFoundError as exc:
                    raise ProjectTransferError("Destination team not found") from exc
                if destination_team.owner_id is None:
                    raise ProjectTransferError("Destination team has no owner")
                await self.project_repository.update_project_transfer(
                    project,
                    team_id=destination_team.id,
                    owner_id=destination_team.owner_id,
                )
            else:
                owner_id = project.owner_id or data.owner_id
                if owner_id is None:
                    raise ProjectTransferError(
                        "An active owner is required when moving this project to standalone"
                    )
                owner = await self.project_repository.get_active_user_by_id(owner_id)
                if owner is None:
                    raise ProjectTransferError("Project owner must be an active user")
                await self.project_repository.update_project_transfer(
                    project,
                    team_id=None,
                    owner_id=owner.id,
                )
                await self.permission_service.add_user_to_project_permissions(
                    owner.id, project.id, Role.ADMIN
                )

            await self.db.commit()
            await self.project_repository.refresh_project_transfer(project)
            loaded = await self.project_repository.get_project_by_id(
                project_id, full_load=True
            )
            return self.project_mapper.project_schema_to_dto(
                loaded,
                SchemaToDTOProps(
                    experiment_count=len(loaded.experiments),
                    hypothesis_count=len(loaded.hypotheses),
                ),
            )
        except Exception as e:
            await self.db.rollback()
            raise e

    async def change_project_owner(
        self,
        user: UserProtocol | None,
        project_id: UUID_TYPE,
        data: ProjectOwnerTransferDTO,
        *,
        admin_bypass: bool = False,
    ) -> ProjectDTO:
        """Transfer ownership of a standalone project to an active user.

        Args:
            user: Authenticated user requesting the transfer, or ``None`` for an
                admin-key operation.
            project_id: Standalone project identifier.
            data: New owner identifier.
            admin_bypass: Whether to bypass user RBAC checks for an admin-key request.

        Returns:
            ProjectDTO: Updated project with the new owner.

        Raises:
            ProjectNotAccessibleError: If the project does not exist.
            ProjectPermissionError: If a regular requester is not the current owner or
                cannot edit the project.
            ProjectTransferError: If the project belongs to a team or the new owner is
                not an active user.
            Exception: Propagates persistence errors after rolling back the transaction.
        """
        try:
            project = await self.project_repository.get_project_by_id(
                project_id, full_load=False
            )
            if project is None:
                raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
            if project.team_id is not None:
                raise ProjectTransferError(
                    "Team project ownership follows the team owner"
                )
            if not admin_bypass:
                if user is None or (
                    project.owner_id != user.id
                    and not getattr(user, "is_superuser", False)
                ):
                    raise ProjectPermissionError(
                        "Only the current owner can transfer project ownership"
                    )
                if not await self.permission_checker.can_edit_project(
                    user.id, project_id
                ):
                    raise ProjectPermissionError(
                        "Current owner does not have permission to edit the project"
                    )

            new_owner = await self.project_repository.get_active_user_by_id(data.owner_id)
            if new_owner is None:
                raise ProjectTransferError("New owner must be an active user")

            await self.project_repository.update_project_transfer(
                project,
                team_id=None,
                owner_id=new_owner.id,
            )
            await self.permission_service.add_user_to_project_permissions(
                new_owner.id, project.id, Role.ADMIN
            )
            await self.db.commit()
            await self.project_repository.refresh_project_transfer(project)
            loaded = await self.project_repository.get_project_by_id(
                project_id, full_load=True
            )
            return self.project_mapper.project_schema_to_dto(
                loaded,
                SchemaToDTOProps(
                    experiment_count=len(loaded.experiments),
                    hypothesis_count=len(loaded.hypotheses),
                ),
            )
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_project_settings(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> list[ProjectSettingDTO]:
        """Return structured settings for a project.

        Args:
            user: User requesting settings.
            project_id: Project identifier.

        Returns:
            list[ProjectSettingDTO]: Validated setting entries.

        Raises:
            ProjectNotAccessibleError: If the project is not visible or cannot be
                loaded.
            pydantic.ValidationError: If stored setting payloads do not match the DTO.
        """
        project = await self.get_project_if_accessible(user, project_id)
        if not project:
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        settings = self._normalize_settings(project.settings)
        return [ProjectSettingDTO.model_validate(item) for item in settings]

    async def get_project_settings_map(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> dict[str, Any]:
        """Return project settings as a name-to-value mapping.

        Args:
            user: User requesting settings.
            project_id: Project identifier.

        Returns:
            dict[str, Any]: Runtime settings keyed by setting name.

        Raises:
            ProjectNotAccessibleError: If project settings cannot be read.
            pydantic.ValidationError: If stored settings are invalid.
        """
        settings = await self.get_project_settings(user, project_id)
        return {setting.name: setting.value for setting in settings}

    async def add_project_settings(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        entries: list[ProjectSettingDTO],
    ) -> list[ProjectSettingDTO]:
        """Append new typed setting entries to a project.

        Args:
            user: User editing settings.
            project_id: Project identifier.
            entries: New settings to append.

        Returns:
            list[ProjectSettingDTO]: Full settings list after append.

        Raises:
            ProjectPermissionError: If the user cannot edit the project.
            ProjectNotAccessibleError: If the project cannot be loaded.
            ValueError: If a setting name is duplicated, already exists, or has a
                value incompatible with its declared type.
        """
        try:
            project_model = await self.project_repository.get_by_id(project_id)
            if not await self.permission_checker.can_edit_project(user.id, project_id):
                raise ProjectPermissionError(
                    f"User {user.id} does not have permission to update project {project_id}"
                )
            existing_settings = self._normalize_settings(project_model.settings)
            existing_names = {str(item.get("name")) for item in existing_settings}
            payload_names = set()
            for entry in entries:
                self._validate_setting_value(entry.type, entry.value)
                if entry.name in payload_names:
                    raise ValueError(f"Duplicate setting name in payload: {entry.name}")
                if entry.name in existing_names:
                    raise ValueError(f"Setting already exists: {entry.name}")
                payload_names.add(entry.name)
            new_entries = [
                entry.model_dump(by_alias=False, mode="json") for entry in entries
            ]
            project_model.settings = [*existing_settings, *new_entries]
            await self.db.commit()
            await self.db.refresh(project_model)
            return [
                ProjectSettingDTO.model_validate(item)
                for item in project_model.settings
            ]
        except DBNotFoundError:
            await self.db.rollback()
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        except Exception as e:
            await self.db.rollback()
            raise e

    async def update_project_setting_value(
        self, user: UserProtocol, project_id: UUID_TYPE, name: str, value: Any
    ) -> ProjectSettingDTO:
        """Update the value of one existing project setting.

        Args:
            user: User editing settings.
            project_id: Project identifier.
            name: Setting name to update.
            value: Replacement value, validated against the stored setting type.

        Returns:
            ProjectSettingDTO: Updated setting entry.

        Raises:
            ProjectPermissionError: If the user cannot edit the project.
            ProjectNotAccessibleError: If the project or setting cannot be loaded.
            ValueError: If ``value`` is incompatible with the setting type.
        """
        try:
            project_model = await self.project_repository.get_by_id(project_id)
            if not await self.permission_checker.can_edit_project(user.id, project_id):
                raise ProjectPermissionError(
                    f"User {user.id} does not have permission to update project {project_id}"
                )
            settings = self._normalize_settings(project_model.settings)
            for idx, item in enumerate(settings):
                if item.get("name") != name:
                    continue
                setting_type = item.get("type")
                self._validate_setting_value(setting_type, value)
                updated_settings = [dict(setting) for setting in settings]
                updated_settings[idx]["value"] = value
                project_model.settings = updated_settings
                await self.db.commit()
                await self.db.refresh(project_model)
                return ProjectSettingDTO.model_validate(updated_settings[idx])
            raise DBNotFoundError(f"Project setting '{name}' does not exist")
        except DBNotFoundError as e:
            await self.db.rollback()
            message = str(e)
            if "Project setting" in message:
                raise ProjectNotAccessibleError(message)
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete_project_setting(
        self, user: UserProtocol, project_id: UUID_TYPE, name: str
    ) -> bool:
        """Remove one setting entry from a project.

        Args:
            user: User editing settings.
            project_id: Project identifier.
            name: Setting name to remove.

        Returns:
            bool: ``True`` after the setting is removed and committed.

        Raises:
            ProjectPermissionError: If the user cannot edit the project.
            ProjectNotAccessibleError: If the project or setting cannot be loaded.
        """
        try:
            project_model = await self.project_repository.get_by_id(project_id)
            if not await self.permission_checker.can_edit_project(user.id, project_id):
                raise ProjectPermissionError(
                    f"User {user.id} does not have permission to update project {project_id}"
                )
            settings = self._normalize_settings(project_model.settings)
            filtered_settings = [item for item in settings if item.get("name") != name]
            if len(filtered_settings) == len(settings):
                raise DBNotFoundError(f"Project setting '{name}' does not exist")
            project_model.settings = filtered_settings
            await self.db.commit()
            return True
        except DBNotFoundError as e:
            await self.db.rollback()
            message = str(e)
            if "Project setting" in message:
                raise ProjectNotAccessibleError(message)
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_accessible_projects(
        self,
        user: UserProtocol,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
        list_options: ListOptions = ListOptions(),
    ) -> ProjectListResponseDTO:
        """List projects accessible to a user.

        Args:
            user: User requesting projects.
            actions: Required action or actions for inclusion.
            list_options: Pagination limit and offset.

        Returns:
            ProjectListResponseDTO: Paginated projects with experiment/hypothesis
            counts.
        """
        project_ids = await self.get_accessible_project_ids(user, actions)
        if not project_ids:
            return ProjectListResponseDTO(
                data=[],
                has_next=False,
                size=0,
                total=0,
            )
        project_page = await self.project_repository.get_projects_by_ids(
            project_ids,
            list_options=list_options,
            full_load=True,
        )
        project_models = project_page.data
        experiment_counts = [
            len(project.experiments) if project.experiments else 0
            for project in project_models
        ]
        hypothesis_counts = [
            len(project.hypotheses) if project.hypotheses else 0
            for project in project_models
        ]
        props = [
            SchemaToDTOProps(
                experiment_count=experiment_count, hypothesis_count=hypothesis_count
            )
            for experiment_count, hypothesis_count in zip(
                experiment_counts, hypothesis_counts
            )
        ]
        return ProjectListResponseDTO(
            data=self.project_mapper.project_list_schema_to_dto(project_models, props),
            has_next=project_page.has_next,
            size=project_page.size,
            total=project_page.total,
        )

    async def get_project_if_accessible(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
    ) -> ProjectDTO | None:
        """Load one project if the user has the requested action.

        Args:
            user: User requesting the project.
            project_id: Project identifier.
            actions: Required action or actions; defaults to project view.

        Returns:
            ProjectDTO | None: Project DTO when accessible and found, otherwise
            ``None``.
        """
        if not await self.is_user_accessible_project(user, project_id, actions=actions):
            return None
        project_model = await self.project_repository.get_project_by_id(
            project_id, full_load=True
        )
        if not project_model:
            return None
        experiment_count = (
            len(project_model.experiments) if project_model.experiments else 0
        )
        hypothesis_count = (
            len(project_model.hypotheses) if project_model.hypotheses else 0
        )
        props = SchemaToDTOProps(
            experiment_count=experiment_count, hypothesis_count=hypothesis_count
        )
        return self.project_mapper.project_schema_to_dto(project_model, props)

    async def is_user_accessible_project(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
    ) -> bool:
        """Check whether a user has the requested access to a project.

        Args:
            user: User whose permission is checked.
            project_id: Project identifier.
            actions: Action or actions to require. ``None`` falls back to project view.

        Returns:
            bool: ``True`` when the permission service grants any requested action.
        """
        if not getattr(user, "is_active", True):
            return False
        if getattr(user, "is_superuser", False):
            return True
        if actions is None:
            actions = ProjectActions.VIEW_PROJECT
        actions_list = [actions] if isinstance(actions, str) else actions
        return await self.permission_service.has_permission(
            user_id=user.id, project_id=project_id, actions=actions_list
        )

    async def delete_project(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        *,
        detailed: bool = False,
    ) -> ProjectDeleteResponseDTO:
        """Delete a project after best-effort satellite teardown.

        The method verifies delete permission, gathers experiment ids, removes
        experiment/project data from object storage and scalars, deletes the Postgres
        project row, and returns a structured cleanup outcome. Failures roll back the
        database transaction.

        Args:
            user: User deleting the project.
            project_id: Project identifier.
            detailed: Whether to include full cleanup result payloads.

        Returns:
            ProjectDeleteResponseDTO: Satellite and Postgres deletion outcome.

        Raises:
            ProjectPermissionError: If the user cannot delete the project.
            ProjectNotAccessibleError: If the project cannot be loaded.
            Exception: Propagates repository errors after rollback.
        """
        try:
            if not await self.permission_checker.can_delete_project(
                user.id, project_id
            ):
                raise ProjectPermissionError(
                    f"User {user.id} does not have permission to delete project {project_id}"
                )
            project = await self.project_repository.get_project_by_id(
                project_id, full_load=True
            )
            if project is None:
                raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
            experiment_ids = [e.id for e in list(project.experiments or [])]
            teardown = await teardown_project_for_delete(
                project_id,
                experiment_ids,
                self.object_storage_client,
                self.scalars_service,
            )
            results, errors = outcome_lists_from_project_teardown(teardown)
            await self.project_repository.delete(project_id)
            await self.db.commit()
            append_postgres_deleted(
                results, category="postgres:project", entity_id=project_id
            )
            finalized = finalize_deletion_outcome(results, errors, detailed=detailed)
            return ProjectDeleteResponseDTO.model_validate(finalized.model_dump())
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_project_usage(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> ProjectUsageDTO:
        """Return JSON-shaped storage totals for the project (object storage + scalars).

        Merges:
        - **Object storage** ``get_project_usage`` — project CAS artifacts, snapshots,
          and per-experiment bucket rollups when the client is configured.
        - **Scalars** ``get_project_usage`` — ClickHouse ``totalBytes`` plus optional
          per-table breakdown for managed tables.

        Computes ``total.bytes`` as the sum of artifact/snapshot/bucket bytes plus scalar
        bytes. Requires ``VIEW_PROJECT`` (via ``can_view_project``).

        Raises:
            ProjectNotAccessibleError: If the user cannot view the project.

        Args:
            user: User requesting usage.
            project_id: Project identifier.

        Returns:
            ProjectUsageDTO: Project artifact, snapshot, experiment bucket, scalar,
            and total usage blocks.
        """
        if not await self.permission_checker.can_view_project(user.id, project_id):
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        object_usage = (
            await self.object_storage_client.get_project_usage(project_id)
            if self.object_storage_client is not None
            else None
        )
        scalar_usage = await self.scalars_service.get_project_usage(project_id)
        if object_usage is None:
            project_artifacts = UsageBytesCountDTO()
            snapshots = UsageBytesCountDTO()
            experiment_buckets = ProjectUsageExperimentBucketsDTO()
        else:
            project_artifacts = UsageBytesCountDTO(
                count=object_usage.project_artifacts.count,
                bytes=object_usage.project_artifacts.bytes,
            )
            snapshots = UsageBytesCountDTO(
                count=object_usage.snapshots.count,
                bytes=object_usage.snapshots.bytes,
            )
            experiment_buckets = ProjectUsageExperimentBucketsDTO(
                count=object_usage.experiment_buckets.count,
                bytes=object_usage.experiment_buckets.bytes,
            )
        scalars = ProjectUsageScalarsDTO(
            bytes=int(scalar_usage.total_bytes),
            tables=[
                ProjectUsageScalarTableDTO(
                    table=t.table,
                    exists=t.exists,
                    rows=t.rows,
                    columns=t.columns,
                    bytes=t.bytes,
                )
                for t in scalar_usage.tables
            ],
        )
        total = (
            project_artifacts.bytes
            + snapshots.bytes
            + experiment_buckets.bytes
            + scalars.bytes
        )
        return ProjectUsageDTO(
            project_id=str(project_id),
            project_artifacts=project_artifacts,
            snapshots=snapshots,
            experiment_buckets=experiment_buckets,
            scalars=scalars,
            total=ProjectUsageTotalDTO(bytes=total),
        )

    async def cleanup_project_category(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        category: ProjectCleanupCategory,
    ) -> CategoryCleanupResponseDTO:
        """Danger-zone **partial** cleanup at project scope (does not delete the Postgres project).

        Categories:
            ``projectArtifacts`` — project CAS blobs only (project bucket metadata + objects).
            ``snapshots`` — all project snapshots (with proper blob ref cleanup).
            ``experimentBuckets`` — experiment-scoped buckets and tracked experiment blobs only.
            ``scalars`` — drops the entire ClickHouse table set for the project via
            ``delete_project_table`` (destructive to **all** experiments' time series in
            that project).

        Response shape matches ``cleanup_experiment_category`` (``success``, ``partial``,
        ``results``, ``errors``) for uniform UI handling.

        Raises:
            ProjectPermissionError: If the user lacks project delete permission.
            ValueError: Unknown ``category`` value.

        Args:
            user: User requesting cleanup.
            project_id: Project identifier.
            category: Storage category to clean.

        Returns:
            CategoryCleanupResponseDTO: Cleanup success/partial state and per-category
            results/errors.
        """
        if not await self.permission_checker.can_delete_project(user.id, project_id):
            raise ProjectPermissionError(
                f"User {user.id} does not have permission to clean project {project_id}"
            )
        results: list[CategoryCleanupResultEntryDTO] = []
        errors: list[CategoryCleanupErrorEntryDTO] = []
        if category in {"projectArtifacts", "snapshots", "experimentBuckets"}:
            if self.object_storage_client is None:
                errors.append(
                    CategoryCleanupErrorEntryDTO(
                        category=category,
                        error="Object storage is not configured",
                    )
                )
            else:
                try:
                    if category == "projectArtifacts":
                        response = await self.object_storage_client.cleanup_project_cas_only(
                            project_id
                        )
                    elif category == "snapshots":
                        response = await self.object_storage_client.cleanup_project_snapshots_only(
                            project_id
                        )
                    else:
                        response = await self.object_storage_client.cleanup_project_experiment_buckets_only(
                            project_id
                        )
                    results.append(
                        CategoryCleanupResultEntryDTO(
                            category=category,
                            result=response.model_dump(),
                        )
                    )
                except Exception as exc:
                    errors.append(
                        CategoryCleanupErrorEntryDTO(
                            category=category,
                            error=str(exc),
                        )
                    )
        elif category == "scalars":
            try:
                res = await self.scalars_service.delete_project_table(project_id)
                results.append(
                    CategoryCleanupResultEntryDTO(
                        category=category,
                        result=res.model_dump(mode="json", by_alias=True),
                    )
                )
            except Exception as exc:
                errors.append(
                    CategoryCleanupErrorEntryDTO(category=category, error=str(exc))
                )
        else:
            raise ValueError(f"Unknown cleanup category: {category}")
        return CategoryCleanupResponseDTO(
            success=not errors,
            partial=bool(results and errors),
            result_count=len(results),
            results=results,
            errors=errors,
        )
