<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Я разрабатывают веб приложение на FastAPI для мониторинга DL экспериментов. Соответственно юзер может создавать проекты, эксперименты (внутри проекта), гипотезы (внутри проекта). Юзер может создавать свои проекты или команды. В команде есть свои проекты и они могут быть частично ограничены для конкретных членов команды. Например кто-то может делать что хочет в проекте, а кто-то может только просматривать. И это можно кастомизировать. Как мне реализовать поддержку всего этого в проекте?

Отлично! Вот полный гайд по реализации системы разрешений для твоего приложения мониторинга DL экспериментов.

## Архитектурный Подход

Я рекомендую использовать **иерархическую RBAC (Role-Based Access Control)** с поддержкой **контекста** (привязка к проекту/команде). Вот структура:

### 1. **Database Schema**

Используй эту структуру БД (я буду использовать SQLAlchemy ORM):

```python
# models/core.py
from sqlalchemy import Column, String, UUID, DateTime, ForeignKey, Table, Boolean, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

# Association tables
team_members = Table(
    'team_members',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id')),
    Column('team_id', UUID(as_uuid=True), ForeignKey('teams.id')),
    Column('role_id', UUID(as_uuid=True), ForeignKey('team_roles.id')),
)

project_members = Table(
    'project_members',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id')),
    Column('project_id', UUID(as_uuid=True), ForeignKey('projects.id')),
    Column('role_id', UUID(as_uuid=True), ForeignKey('project_roles.id')),
)

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    hashed_password: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    teams: Mapped[list["Team"]] = relationship(secondary=team_members)
    projects: Mapped[list["Project"]] = relationship(secondary=project_members)
    personal_projects: Mapped[list["Project"]] = relationship(back_populates="owner")

class Team(Base):
    __tablename__ = "teams"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str]
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    members: Mapped[list["User"]] = relationship(secondary=team_members)
    projects: Mapped[list["Project"]] = relationship(back_populates="team")
    roles: Mapped[list["TeamRole"]] = relationship(back_populates="team")

class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str]
    description: Mapped[str | None]
    is_team_project: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Foreign Keys
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    
    # Relationships
    owner: Mapped["User"] = relationship(back_populates="personal_projects")
    team: Mapped["Team | None"] = relationship(back_populates="projects")
    members: Mapped[list["User"]] = relationship(secondary=project_members)
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="project")
    hypotheses: Mapped[list["Hypothesis"]] = relationship(back_populates="project")

class Experiment(Base):
    __tablename__ = "experiments"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str]
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    project: Mapped["Project"] = relationship(back_populates="experiments")
    hypotheses: Mapped[list["Hypothesis"]] = relationship(back_populates="experiment")

class Hypothesis(Base):
    __tablename__ = "hypotheses"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str]
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    project: Mapped["Project"] = relationship(back_populates="hypotheses")

# Permission и Role Models
class Permission(Base):
    __tablename__ = "permissions"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(unique=True)  # e.g., "project:read", "project:write", "project:delete"
    description: Mapped[str | None]

class TeamRole(Base):
    __tablename__ = "team_roles"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"))
    name: Mapped[str]  # e.g., "Admin", "Editor", "Viewer"
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=Table(
            'team_role_permissions',
            Base.metadata,
            Column('role_id', UUID(as_uuid=True), ForeignKey('team_roles.id')),
            Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id')),
        )
    )
    
    team: Mapped["Team"] = relationship(back_populates="roles")

class ProjectRole(Base):
    __tablename__ = "project_roles"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str]  # e.g., "Owner", "Editor", "Viewer"
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=Table(
            'project_role_permissions',
            Base.metadata,
            Column('role_id', UUID(as_uuid=True), ForeignKey('project_roles.id')),
            Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id')),
        )
    )
    
    project: Mapped["Project"] = relationship()
```


### 2. **Permission System с Dependency Injection**

```python
# auth/permissions.py
from typing import List
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
import uuid

class PermissionChecker:
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        project_id: uuid.UUID = None,  # Pass as path param
    ) -> User:
        """
        Проверяет, есть ли у пользователя нужные разрешения на проект
        """
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id required")
        
        # Получаем проект
        project = db.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Проверяем доступ
        user_permissions = await self._get_user_permissions(
            current_user, project, db
        )
        
        # Проверяем наличие требуемых разрешений
        for perm in self.required_permissions:
            if perm not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {perm}"
                )
        
        return current_user
    
    async def _get_user_permissions(
        self, user: User, project: Project, db: Session
    ) -> set[str]:
        """
        Получает все разрешения пользователя для проекта
        """
        permissions = set()
        
        # 1. Проверяем, является ли пользователь владельцем личного проекта
        if project.owner_id == user.id:
            permissions.update([
                "project:read", "project:write", "project:delete",
                "experiment:create", "experiment:read", "experiment:write", "experiment:delete",
                "hypothesis:create", "hypothesis:read", "hypothesis:write", "hypothesis:delete",
            ])
            return permissions
        
        # 2. Проверяем роль в команде (если это проект команды)
        if project.team_id:
            team_role = db.execute(
                select(TeamRole).join(
                    team_members
                ).where(
                    team_members.c.user_id == user.id,
                    team_members.c.team_id == project.team_id,
                )
            ).scalar_one_or_none()
            
            if team_role:
                for perm in team_role.permissions:
                    permissions.add(perm.name)
        
        # 3. Проверяем прямую роль в проекте
        project_role = db.execute(
            select(ProjectRole).join(
                project_members
            ).where(
                project_members.c.user_id == user.id,
                project_members.c.project_id == project.id,
            )
        ).scalar_one_or_none()
        
        if project_role:
            for perm in project_role.permissions:
                permissions.add(perm.name)
        
        return permissions


# Быстрые проверки
async def require_permission(
    permissions: List[str] = ["project:read"]
):
    """Factory для создания PermissionChecker"""
    return PermissionChecker(permissions)
```


### 3. **Endpoints с защитой**

```python
# routes/projects.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/{project_id}")
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission(["project:read"])),
    db: Session = Depends(get_db),
):
    """Получить проект (с проверкой прав)"""
    project = db.execute(
        select(Project).where(Project.id == project_id)
    ).scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"id": project.id, "name": project.name}

@router.post("/{project_id}/experiments")
async def create_experiment(
    project_id: uuid.UUID,
    name: str,
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission(["experiment:create"])),
    db: Session = Depends(get_db),
):
    """Создать эксперимент (требует разрешения)"""
    project = db.execute(
        select(Project).where(Project.id == project_id)
    ).scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    experiment = Experiment(project_id=project_id, name=name)
    db.add(experiment)
    db.commit()
    
    return {"id": experiment.id, "name": experiment.name}

@router.post("/{project_id}/members")
async def add_team_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission(["project:write"])),  # Только редакторы
    db: Session = Depends(get_db),
):
    """Добавить члена команды (требует разрешения на редактирование)"""
    project = db.execute(
        select(Project).where(Project.id == project_id)
    ).scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Привязываем роль к пользователю в проекте
    # ... логика
    
    return {"success": True}
```


### 4. **Предустановки ролей и разрешений**

```python
# auth/defaults.py
from enum import Enum

class PermissionEnum(str, Enum):
    # Project permissions
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    PROJECT_MANAGE_MEMBERS = "project:manage_members"
    
    # Experiment permissions
    EXPERIMENT_CREATE = "experiment:create"
    EXPERIMENT_READ = "experiment:read"
    EXPERIMENT_WRITE = "experiment:write"
    EXPERIMENT_DELETE = "experiment:delete"
    
    # Hypothesis permissions
    HYPOTHESIS_CREATE = "hypothesis:create"
    HYPOTHESIS_READ = "hypothesis:read"
    HYPOTHESIS_WRITE = "hypothesis:write"
    HYPOTHESIS_DELETE = "hypothesis:delete"

class DefaultTeamRoles:
    """Предустановки ролей для команд"""
    
    ADMIN = {
        "name": "Admin",
        "permissions": [
            PermissionEnum.PROJECT_READ,
            PermissionEnum.PROJECT_WRITE,
            PermissionEnum.PROJECT_DELETE,
            PermissionEnum.PROJECT_MANAGE_MEMBERS,
            PermissionEnum.EXPERIMENT_CREATE,
            PermissionEnum.EXPERIMENT_READ,
            PermissionEnum.EXPERIMENT_WRITE,
            PermissionEnum.EXPERIMENT_DELETE,
            PermissionEnum.HYPOTHESIS_CREATE,
            PermissionEnum.HYPOTHESIS_READ,
            PermissionEnum.HYPOTHESIS_WRITE,
            PermissionEnum.HYPOTHESIS_DELETE,
        ]
    }
    
    EDITOR = {
        "name": "Editor",
        "permissions": [
            PermissionEnum.PROJECT_READ,
            PermissionEnum.PROJECT_WRITE,
            PermissionEnum.EXPERIMENT_CREATE,
            PermissionEnum.EXPERIMENT_READ,
            PermissionEnum.EXPERIMENT_WRITE,
            PermissionEnum.HYPOTHESIS_CREATE,
            PermissionEnum.HYPOTHESIS_READ,
            PermissionEnum.HYPOTHESIS_WRITE,
        ]
    }
    
    VIEWER = {
        "name": "Viewer",
        "permissions": [
            PermissionEnum.PROJECT_READ,
            PermissionEnum.EXPERIMENT_READ,
            PermissionEnum.HYPOTHESIS_READ,
        ]
    }

class DefaultProjectRoles:
    """Предустановки ролей для проектов"""
    
    OWNER = {
        "name": "Owner",
        "permissions": [
            perm for perm in PermissionEnum
        ]
    }
    
    COLLABORATOR = {
        "name": "Collaborator",
        "permissions": [
            PermissionEnum.PROJECT_READ,
            PermissionEnum.PROJECT_WRITE,
            PermissionEnum.EXPERIMENT_CREATE,
            PermissionEnum.EXPERIMENT_READ,
            PermissionEnum.EXPERIMENT_WRITE,
            PermissionEnum.HYPOTHESIS_CREATE,
            PermissionEnum.HYPOTHESIS_READ,
            PermissionEnum.HYPOTHESIS_WRITE,
        ]
    }
    
    VIEWER = {
        "name": "Viewer",
        "permissions": [
            PermissionEnum.PROJECT_READ,
            PermissionEnum.EXPERIMENT_READ,
            PermissionEnum.HYPOTHESIS_READ,
        ]
    }
```


### 5. **Кастомизация разрешений (Advanced)**

```python
# routes/admin.py - управление ролями и разрешениями
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/teams/{team_id}/roles")
async def create_custom_role(
    team_id: uuid.UUID,
    role_name: str,
    permissions: List[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Создать кастомную роль в команде"""
    
    # Проверяем, является ли пользователь админом команды
    # ... проверка
    
    # Создаем роль
    new_role = TeamRole(team_id=team_id, name=role_name)
    
    # Добавляем разрешения
    for perm_name in permissions:
        permission = db.execute(
            select(Permission).where(Permission.name == perm_name)
        ).scalar_one_or_none()
        
        if permission:
            new_role.permissions.append(permission)
    
    db.add(new_role)
    db.commit()
    
    return {"id": new_role.id, "name": new_role.name, "permissions": permissions}

@router.put("/projects/{project_id}/members/{user_id}/role")
async def update_member_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Изменить роль члена проекта"""
    
    # Проверяем права текущего пользователя
    # ... проверка
    
    # Обновляем роль
    # ...
    
    return {"success": True}
```


## Key Points:

1. **Иерархия доступа**: Личный проект (максимум прав) → Проект команды → Прямое назначение в проекте
2. **Гибкость**: Разрешения комбинируются в роли, роли назначаются пользователям
3. **Performance**: Кешируй разрешения пользователя на сессию (можешь использовать Redis)
4. **Scalability**: SQL запросы с индексами по `user_id`, `project_id`, `team_id`

Хочешь, я покажу реализацию **кеширования разрешений** или **аудита изменений доступа**?
<span style="display:none">[^1_1][^1_10][^1_11][^1_12][^1_13][^1_14][^1_15][^1_2][^1_3][^1_4][^1_5][^1_6][^1_7][^1_8][^1_9]</span>

<div align="center">⁂</div>

[^1_1]: https://app-generator.dev/docs/technologies/fastapi/rbac.html

[^1_2]: http://www.zigpoll.com/content/what-database-schema-do-you-recommend-using-to-efficiently-manage-owner-permissions-and-roles-across-multiple-projects

[^1_3]: https://stackoverflow.com/questions/79285538/add-auth-to-fastapi-via-middleware-and-include-in-openapi

[^1_4]: https://www.youtube.com/watch?v=RRG5l8wJoTI

[^1_5]: https://www.tencentcloud.com/techpedia/122735

[^1_6]: https://www.propelauth.com/post/fastapi-auth-with-dependency-injection

[^1_7]: https://www.reddit.com/r/FastAPI/comments/1jn1203/how_do_you_handle_rebac_abac_and_rbac_in_fastapi/

[^1_8]: https://www.cerbos.dev/blog/designing-an-authorization-model-for-an-enterprise

[^1_9]: https://fastapi-keycloak-middleware.readthedocs.io/en/latest/authorization.html

[^1_10]: https://auth0.com/blog/implementing-rbac-fastapi-auth0-fga/

[^1_11]: https://blog.montrealanalytics.com/role-based-access-control-for-data-teams-part-1-617a768e6f3f

[^1_12]: https://pypi.org/project/fastapi-auth-middlewares/

[^1_13]: https://www.permit.io/blog/fastapi-rbac-full-implementation-tutorial

[^1_14]: https://learn.microsoft.com/en-us/azure/devops/boards/plans/configure-hierarchical-teams?view=azure-devops

[^1_15]: https://www.oneloop.ai/blog/setting-up-middleware-in-fastapi


---

# А что делать для конкретного проекта? если я хочу ограничить доступ к конкретному проекту

Для ограничения доступа к **конкретному проекту** внутри команды (например, "Секретный Проект" внутри команды "ML Engineers"), нужно внедрить концепцию **"Приватности Проекта"** и **"Явного Членства"**.

Вот как это реализовать поверх предыдущей схемы.

### 1. Изменение Схемы БД (Project Visibility)

Добавь поле `visibility` в модель `Project`. Это определит, наследуют ли члены команды доступ автоматически.

```python
import enum
from sqlalchemy import Enum as PgEnum

class ProjectVisibility(str, enum.Enum):
    TEAM = "team"       # Виден всем участникам команды (как Viewer или выше)
    PRIVATE = "private" # Виден ТОЛЬКО тем, кто явно добавлен в project_members

class Project(Base):
    # ... существующие поля ...
    visibility: Mapped[ProjectVisibility] = mapped_column(
        PgEnum(ProjectVisibility), 
        default=ProjectVisibility.TEAM
    )
```


### 2. Обновленная Логика Проверки Прав

Логика `PermissionChecker` должна теперь работать так:

1. Если проект **Private**, игнорируем роль в команде. Смотрим *только* на таблицу `project_members`.
2. Если проект **Team** (публичный для команды), берем права из команды.
3. **Override (Важно):** Если юзер есть *и* в команде, *и* явно добавлен в проект, роль в проекте должна иметь приоритет (или объединяться). Обычно для безопасности приоритет отдается **более специфичной роли** (проектной).

Вот обновленный метод `_get_user_permissions`:

```python
async def _get_user_permissions(
    self, user: User, project: Project, db: Session
) -> set[str]:
    permissions = set()
    
    # 1. Владелец всегда имеет полный доступ
    if project.owner_id == user.id:
        return self._get_full_permissions()

    # 2. Проверяем явную роль в проекте (ProjectRole)
    # Это переопределяет (или дополняет) командную роль
    project_role = db.execute(
        select(ProjectRole).join(project_members).where(
            project_members.c.user_id == user.id,
            project_members.c.project_id == project.id,
        )
    ).scalar_one_or_none()

    if project_role:
        for perm in project_role.permissions:
            permissions.add(perm.name)
            
    # 3. Если проект ПУБЛИЧНЫЙ для команды и у юзера НЕТ явной блокировки
    # (если вы хотите strict private, то шаг 3 выполняется только если visibility == TEAM)
    if project.visibility == ProjectVisibility.TEAM and project.team_id:
        team_role = db.execute(
            select(TeamRole).join(team_members).where(
                team_members.c.user_id == user.id,
                team_members.c.team_id == project.team_id,
            )
        ).scalar_one_or_none()
        
        if team_role:
            for perm in team_role.permissions:
                permissions.add(perm.name)

    return permissions
```


### 3. Сценарии Использования

Вот как это решает твои задачи:

#### Сценарий А: "Секретный проект в команде"

* Создаешь проект в команде c `visibility = PRIVATE`.
* По умолчанию **никто** из команды его не видит (кроме создателя).
* Ты вручную добавляешь Васю и Петю в `project_members` (таблица связи `users <-> projects`).
* **Итог:** Вася и Петя видят проект, Коля (тоже из команды) — нет.


#### Сценарий Б: "Внешний Аудитор" (Гость)

* Есть проект внутри команды.
* Приглашаешь человека *извне* (он не член команды `Team`).
* Просто добавляешь его в `project_members` с ролью `Viewer`.
* **Итог:** Он видит ТОЛЬКО этот проект, но не видит другие проекты команды.


#### Сценарий В: "Повышение прав" (Override)

* В команде Вася — `Viewer` (может только смотреть).
* Для конкретного проекта "Эксперимент X" ты добавляешь Васю в `project_members` с ролью `Editor`.
* **Итог:** Вася видит все проекты команды (как Viewer), но в "Эксперименте X" может создавать гипотезы.[^2_1]


### 4. API для управления доступом к проекту

Тебе понадобятся эндпоинты для управления именно проектными доступами:

```python
@router.put("/projects/{project_id}/visibility")
async def update_visibility(
    project_id: uuid.UUID,
    visibility: ProjectVisibility,
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission(["project:write"])), # Нужны права админа/владельца
    db: Session = Depends(get_db)
):
    """Сделать проект приватным или командным"""
    # ... update logic ...
    return {"status": "updated"}

@router.post("/projects/{project_id}/members")
async def add_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    # ...
):
    """Добавить конкретного юзера в проект (даже если он не в команде)"""
    # ... logic ...
```


### Рекомендация для UI

В интерфейсе создания проекта сделай переключатель:

* 🔘 **Visible to Team** (Все участники команды видят проект)
* 🔘 **Private** (Только приглашенные участники)

Это стандартный паттерн (как в GitHub/GitLab/Jira), который будет понятен твоим пользователям.[^2_2][^2_3]
<span style="display:none">[^2_10][^2_11][^2_12][^2_13][^2_14][^2_15][^2_4][^2_5][^2_6][^2_7][^2_8][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: https://flowfuse.com/docs/user/role-based-access-control/

[^2_2]: https://tecnofor.es/en/team-managed-projects-vs-company-managed-projects/

[^2_3]: https://support.atlassian.com/jira-service-management-cloud/docs/overview-of-permissions-in-team-managed-service-projects/

[^2_4]: https://www.matia.io/blog/what-is-role-based-access-control-a-modern-guide-for-data-teams

[^2_5]: https://learn.microsoft.com/en-us/azure/role-based-access-control/overview

[^2_6]: https://blog.montrealanalytics.com/role-based-access-control-for-data-teams-part-1-617a768e6f3f

[^2_7]: https://www.reddit.com/r/snowflake/comments/14xo3ae/schemabased_rbac_design_is_it_practical_in_real/

[^2_8]: https://stackoverflow.com/questions/7329150/db-schema-for-rbac-with-multiple-levels-of-roles

[^2_9]: https://docs.digital.ai/teamforge/docs/projectadmin-controllingprojectaccess

[^2_10]: https://aerospike.com/blog/role-based-access-control-rbac-guide/

[^2_11]: https://support.teamwork.com/projects/project-sections/setting-user-permissions-on-a-project

[^2_12]: https://www.deltastream.io/blog/data-governance-for-teams-rbac/

[^2_13]: https://nordlayer.com/learn/access-control/role-based-access-control-implementation/

[^2_14]: https://www.osohq.com/learn/rbac-role-based-access-control

[^2_15]: https://forum.asana.com/t/team-permissions-vs-project-permissions/833954


---

# Как реализовать ABAC в данной ситуации?

Отличный вопрос! ABAC (Attribute-Based Access Control) даст тебе намного больше гибкости. Вот как это реализовать для системы мониторинга DL экспериментов.

## RBAC vs ABAC: в чем разница?

| Аспект | RBAC | ABAC |
| :-- | :-- | :-- |
| **Принцип** | Фиксированные роли (Admin, Editor, Viewer) | Динамические атрибуты (кто, что, где, когда) |
| **Сложность** | Простая | Сложная, но гибкая |
| **Примеры правил** | "Если роль = Admin, то разрешить" | "Если (роль = Reviewer) И (проект.статус = на_рассмотрении) И (час >= 9 и час <= 18), то разрешить" |
| **Масштабируемость** | Страдает от "role explosion" | Масштабируется лучше |

## Для твоей ситуации ABAC отвечает на вопросы:

- ✅ Разрешить ли Васе **читать** эксперимент, если он **владелец проекта**, но эксперимент **еще в статусе Draft**?
- ✅ Разрешить ли Пете **редактировать** гипотезу, если его **роль = Reviewer**, но **эксперимент уже закончился**?
- ✅ Разрешить ли **скачать** результаты, если пользователь **из другой команды**, но **проект публичен**?


## Реализация ABAC в FastAPI + твоя схема БД

### 1. Модель данных для атрибутов

```python
# models/attributes.py
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, Mapped

class ExperimentStatus(str, Enum):
    DRAFT = "draft"           # Черновик
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"

class Experiment(Base):
    # ... existing fields ...
    
    status: Mapped[ExperimentStatus] = mapped_column(
        default=ExperimentStatus.DRAFT
    )
    is_public: Mapped[bool] = mapped_column(default=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None]
    
    # Метаданные для ABAC
    metadata_: Mapped[dict] = mapped_column(JSON, default={})
    # Пример: {"priority": "high", "ml_framework": "pytorch", "gpu_required": True}

class Project(Base):
    # ... existing fields ...
    status: Mapped[ProjectStatus] = mapped_column(default=ProjectStatus.ACTIVE)
    is_public: Mapped[bool] = mapped_column(default=False)
    
    # Метаданные
    metadata_: Mapped[dict] = mapped_column(JSON, default={})
    # Пример: {"department": "research", "budget_approved": True}

class User(Base):
    # ... existing fields ...
    department: Mapped[str | None]
    clearance_level: Mapped[int] = mapped_column(default=0)  # 0=user, 1=lead, 2=manager
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login: Mapped[datetime | None]
    
    # Метаданные пользователя
    metadata_: Mapped[dict] = mapped_column(JSON, default={})
    # Пример: {"office_location": "Moscow", "specialization": "computer_vision"}
```


### 2. Policy Engine (Движок политик)

Создаем отдельный сервис для оценки политик ABAC:

```python
# auth/policy_engine.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List
from enum import Enum
import re

@dataclass
class PolicyContext:
    """Контекст для оценки политики"""
    user: User
    resource: Project | Experiment | Hypothesis
    action: str  # "read", "write", "delete", "share"
    environment: Dict[str, Any]  # {"time": datetime, "ip": "...", "device": "..."}

class PolicyCondition(str, Enum):
    """Поддерживаемые операторы в политиках"""
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    IN = "in"
    CONTAINS = "contains"
    MATCHES_REGEX = "regex"

class ABACPolicyEngine:
    """
    Движок для оценки политик на основе атрибутов.
    Политики хранятся в БД или конфиге.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.policies = self._load_policies()
    
    def evaluate(self, context: PolicyContext) -> bool:
        """
        Основной метод для проверки доступа.
        Возвращает True, если доступ разрешен.
        """
        # 1. Базовые checks (владелец всегда может)
        if self._is_owner(context):
            return True
        
        # 2. Проверяем явный DENY (если есть)
        if self._has_deny_rule(context):
            return False
        
        # 3. Оцениваем политики
        for policy in self.policies:
            if policy.applies_to(context):
                if self._evaluate_conditions(policy, context):
                    return True
        
        return False
    
    def _is_owner(self, context: PolicyContext) -> bool:
        """Проверяем, является ли пользователь владельцем"""
        if hasattr(context.resource, 'owner_id'):
            return context.resource.owner_id == context.user.id
        
        if hasattr(context.resource, 'project_id'):
            # Для Experiment/Hypothesis проверяем владельца проекта
            project = context.resource.project
            return project.owner_id == context.user.id
        
        return False
    
    def _has_deny_rule(self, context: PolicyContext) -> bool:
        """Проверяем явные запреты (DENY)"""
        # Пример: заблокированный пользователь
        if not context.user.is_active:
            return True
        
        # Пример: приватный проект и пользователь не в team_members
        if hasattr(context.resource, 'visibility'):
            if context.resource.visibility == ProjectVisibility.PRIVATE:
                if context.user not in context.resource.members:
                    return True
        
        return False
    
    def _evaluate_conditions(self, policy: 'Policy', context: PolicyContext) -> bool:
        """Оцениваем условия политики"""
        for condition in policy.conditions:
            if not self._eval_condition(condition, context):
                return False
        return True
    
    def _eval_condition(self, condition: Dict[str, Any], context: PolicyContext) -> bool:
        """
        Оцениваем одно условие.
        Формат: {"attribute": "experiment.status", "operator": "==", "value": "completed"}
        """
        attr_path = condition.get("attribute")
        operator = condition.get("operator")
        expected_value = condition.get("value")
        
        # Получаем значение атрибута
        actual_value = self._get_attribute(attr_path, context)
        
        if actual_value is None:
            return False
        
        # Сравниваем
        if operator == "==":
            return actual_value == expected_value
        elif operator == "!=":
            return actual_value != expected_value
        elif operator == ">":
            return actual_value > expected_value
        elif operator == "<":
            return actual_value < expected_value
        elif operator == "in":
            return actual_value in expected_value
        elif operator == "contains":
            return expected_value in str(actual_value)
        elif operator == "regex":
            return bool(re.match(expected_value, str(actual_value)))
        
        return False
    
    def _get_attribute(self, attr_path: str, context: PolicyContext) -> Any:
        """
        Получаем значение атрибута из контекста.
        Пример: "user.department" или "resource.status" или "environment.time"
        """
        parts = attr_path.split(".")
        
        if parts[^3_0] == "user":
            obj = context.user
        elif parts[^3_0] == "resource":
            obj = context.resource
        elif parts[^3_0] == "environment":
            obj = context.environment
        elif parts[^3_0] == "action":
            return context.action
        else:
            return None
        
        # Проходим по цепочке атрибутов
        for part in parts[1:]:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = getattr(obj, part, None)
            
            if obj is None:
                return None
        
        return obj
    
    def _load_policies(self) -> List['Policy']:
        """Загружаем политики из БД или конфига"""
        # Пока заглушка, см. следующий раздел
        return []

@dataclass
class Policy:
    """Структура политики"""
    name: str
    description: str
    resource_type: str  # "experiment", "project", "hypothesis"
    action: str  # "read", "write", "delete"
    roles: List[str]  # ["editor", "reviewer"]
    conditions: List[Dict[str, Any]]  # Условия для оценки
    effect: str = "ALLOW"  # "ALLOW" или "DENY"
    priority: int = 0  # Для разрешения конфликтов
    
    def applies_to(self, context: PolicyContext) -> bool:
        """Проверяем, применима ли эта политика к контексту"""
        # Проверяем тип ресурса
        resource_type = context.resource.__class__.__name__.lower()
        if self.resource_type != resource_type:
            return False
        
        # Проверяем действие
        if self.action != context.action:
            return False
        
        # Проверяем роли пользователя в контексте
        user_roles = self._get_user_roles(context)
        if not any(role in self.roles for role in user_roles):
            return False
        
        return True
    
    def _get_user_roles(self, context: PolicyContext) -> List[str]:
        """Получаем роли пользователя (из БД или из TeamRole/ProjectRole)"""
        # Упрощенная версия
        roles = []
        
        if hasattr(context.resource, 'team'):
            # Получаем командную роль
            team_role = ...  # query
            if team_role:
                roles.append(team_role.name.lower())
        
        if hasattr(context.resource, 'id'):
            # Получаем роль в проекте
            project_role = ...  # query
            if project_role:
                roles.append(project_role.name.lower())
        
        return roles
```


### 3. Примеры политик для твоего case

```python
# auth/default_policies.py
from auth.policy_engine import Policy, PolicyCondition

DEFAULT_POLICIES = [
    # Политика 1: Редакторы могут редактировать только DRAFT эксперименты
    Policy(
        name="edit_draft_experiments",
        description="Editors can only edit draft experiments",
        resource_type="experiment",
        action="write",
        roles=["editor", "admin"],
        conditions=[
            {"attribute": "resource.status", "operator": "==", "value": "draft"}
        ],
        priority=10
    ),
    
    # Политика 2: Reviewers могут читать эксперименты, если проект активен
    Policy(
        name="reviewer_active_projects",
        description="Reviewers can read experiments from active projects",
        resource_type="experiment",
        action="read",
        roles=["reviewer"],
        conditions=[
            {"attribute": "resource.project.status", "operator": "==", "value": "active"}
        ],
        priority=10
    ),
    
    # Политика 3: Никто не может редактировать завершенные эксперименты
    Policy(
        name="no_edit_completed",
        description="No one can edit completed experiments",
        resource_type="experiment",
        action="write",
        roles=["*"],  # Any role
        conditions=[
            {"attribute": "resource.status", "operator": "==", "value": "completed"}
        ],
        effect="DENY",
        priority=100  # High priority for deny rules
    ),
    
    # Политика 4: Доступ только в рабочее время для sensitive проектов
    Policy(
        name="office_hours_sensitive",
        description="Sensitive projects accessible only during office hours",
        resource_type="project",
        action="read",
        roles=["viewer", "editor", "admin"],
        conditions=[
            {"attribute": "resource.metadata_.budget_approved", "operator": "==", "value": True},
            {"attribute": "environment.hour", "operator": ">=", "value": 9},
            {"attribute": "environment.hour", "operator": "<=", "value": 18}
        ],
        priority=20
    ),
    
    # Политика 5: Сотрудники одного отдела могут делиться проектами
    Policy(
        name="same_department_sharing",
        description="Users from same department can access each other's projects",
        resource_type="project",
        action="read",
        roles=["*"],
        conditions=[
            {"attribute": "user.department", "operator": "==", "value": "resource.metadata_.department"}
        ],
        priority=15
    ),
]
```


### 4. Интеграция с FastAPI

```python
# auth/dependencies.py
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

async def require_action(
    action: str,  # "read", "write", "delete", "share"
):
    """Factory для создания проверки доступа к действию"""
    
    async def _check_action(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        project_id: uuid.UUID = None,
        experiment_id: uuid.UUID = None,
    ) -> User:
        # Определяем ресурс
        resource = None
        if experiment_id:
            resource = db.execute(
                select(Experiment).where(Experiment.id == experiment_id)
            ).scalar_one_or_none()
        elif project_id:
            resource = db.execute(
                select(Project).where(Project.id == project_id)
            ).scalar_one_or_none()
        
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        # Собираем контекст
        context = PolicyContext(
            user=current_user,
            resource=resource,
            action=action,
            environment={
                "time": datetime.utcnow(),
                "hour": datetime.utcnow().hour,
                "day": datetime.utcnow().weekday(),
            }
        )
        
        # Оцениваем политики
        engine = ABACPolicyEngine(db)
        if not engine.evaluate(context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: cannot {action} this resource"
            )
        
        return current_user
    
    return _check_action

# Использование в эндпоинтах:
@router.post("/experiments/{experiment_id}/hypotheses")
async def create_hypothesis(
    experiment_id: uuid.UUID,
    hypothesis_name: str,
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_action("write")),  # ← Проверка ABAC
    db: Session = Depends(get_db),
):
    """Создать гипотезу (с проверкой политик)"""
    # ... логика ...
```


### 5. Управление политиками (Admin панель)

```python
@router.post("/admin/policies")
async def create_policy(
    policy_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Создать новую политику"""
    # Проверяем, что пользователь админ
    # ...
    
    # Добавляем политику в БД или кеш
    new_policy = Policy(**policy_data)
    
    # Логируем для аудита
    # ...
    
    return {"id": new_policy.id, "name": new_policy.name}

@router.get("/admin/policies/audit")
async def get_audit_log(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить логи доступа для аудита"""
    # Все denied attempts должны логироваться
    return db.execute(select(AccessLog).order_by(-AccessLog.created_at)).all()
```


## ABAC vs RBAC в твоей ситуации

| Сценарий | RBAC | ABAC |
| :-- | :-- | :-- |
| "Вася — Editor" | ✅ Может редактировать все проекты | ❌ Может редактировать только Draft эксперименты |
| "Доступ только в рабочее время" | ❌ Невозможно | ✅ Одна политика: `resource.time >= 9 AND time <= 18` |
| "Сотрудники одного отдела видят друг друга" | ❌ Нужно создавать много ролей | ✅ `user.department == resource.owner.department` |
| "Разные наборы прав для Draft vs Completed" | ❌ Нужно много ролей | ✅ Условие: `resource.status` |

## Рекомендация

Начни с **гибридного подхода**:

1. **RBAC** как основа (Admin, Editor, Viewer)
2. **ABAC** для сложных case (статусы, время, атрибуты)

Это даст тебе простоту базовых ролей + гибкость исключений. 🚀
<span style="display:none">[^3_1][^3_10][^3_11][^3_12][^3_13][^3_14][^3_15][^3_2][^3_3][^3_4][^3_5][^3_6][^3_7][^3_8][^3_9]</span>

<div align="center">⁂</div>

[^3_1]: https://www.permit.io/blog/how-to-implement-abac

[^3_2]: https://www.barracuda.com/support/glossary/rbac-vs-abac

[^3_3]: https://www.permit.io/blog/implement-authorization-in-fastapi

[^3_4]: https://www.knostic.ai/blog/attribute-based-access-control-example

[^3_5]: https://www.splunk.com/en_us/blog/learn/rbac-vs-abac.html

[^3_6]: https://www.reddit.com/r/FastAPI/comments/1jn1203/how_do_you_handle_rebac_abac_and_rbac_in_fastapi/

[^3_7]: https://workos.com/blog/attribute-based-access-control-example

[^3_8]: https://www.okta.com/identity-101/role-based-access-control-vs-attribute-based-access-control/

[^3_9]: https://dev.to/mochafreddo/building-a-modern-user-permission-management-system-with-fastapi-sqlalchemy-and-mariadb-5fp1

[^3_10]: https://auth0.com/blog/what-is-abac-and-how-to-implement-it-rails-api/

[^3_11]: https://frontegg.com/guides/rbac-vs-abac

[^3_12]: https://www.permit.io/blog/fastapi-rbac-full-implementation-tutorial

[^3_13]: https://netwrix.com/en/resources/blog/attribute-based-access-control-abac/

[^3_14]: https://www.permit.io/blog/rbac-vs-abac

[^3_15]: https://auth0.com/blog/rebac-abac-openfga-cedar/


---

# А есть готовые библиотеки для этого?

Вот полный обзор! Есть несколько отличных готовых решений:

## Топ 4 библиотеки для FastAPI[^4_1][^4_2][^4_3]

### 1. **Casbin (PyCasbin)** — Мой топ выбор для твоего case ⭐

```python
pip install pycasbin
```

**Почему:**

- ✅ Поддерживает RBAC + ABAC + ACL одновременно
- ✅ Встраивается в код (embedded), не нужен внешний сервис
- ✅ Высокая производительность
- ✅ Легко интегрируется в FastAPI

**Пример работы:**

```python
from pycasbin import Enforcer

enforcer = Enforcer("model.conf", "policy.csv")

# Проверка прав
if enforcer.enforce("vasya", "/projects/123", "write", "experiment"):
    # Разрешаем
else:
    # Запрещаем
```


***

### 2. **Oso** — Самое простое решение

```python
pip install oso
```

**Почему:**

- ✅ Супер простой синтаксис (язык Polar)
- ✅ RBAC + ABAC + ReBAC поддерживаются
- ✅ Очень быстро настраивается

**Пример:**

```python
from oso import Oso

oso = Oso()
oso.load_str("""
allow(actor, "write", experiment) if
  actor.role = "editor" and
  experiment.status = "draft";
""")

allowed = oso.is_allowed(user, "write", experiment)
```


***

### 3. **Permit.io** — Для Enterprise[^4_4][^4_5]

```python
pip install permit-python-sdk
```

**Почему:**

- ✅ Cloud-hosted (не нужно самому управлять)
- ✅ UI для управления политиками
- ✅ Multi-tenant из коробки
- ✅ Аудит и логирование

```python
from permit import Permit

permit = Permit(token="your_api_key")

allowed = await permit.check(
    user_id="vasya",
    action="write",
    resource={"type": "experiment"}
)
```


***

### 4. **py-abac** — Чистое ABAC[^4_6][^4_7]

```python
pip install py-abac
```

**Почему:**

- ✅ Специализирована на ABAC
- ✅ Стандарт XACML (Enterprise-grade)

***

## Сравнение для твоей ситуации

| Критерий | Casbin | Oso | Permit.io | py-abac |
| :-- | :-- | :-- | :-- | :-- |
| RBAC | ✅ | ✅ | ✅ | ❌ |
| ABAC | ✅ | ✅ | ✅ | ✅✅ |
| Простота | 7/10 | 9/10 | 8/10 | 6/10 |
| Performance | 9/10 | 7/10 | 8/10 | 7/10 |
| Встроено | ✅ | ✅ | ❌ Cloud | ✅ |
| Документация | 8/10 | 9/10 | 8/10 | 6/10 |


***

## Мой рецепт для твоего проекта:

**Начни с Casbin**, потому что:

1. Поддерживает **и RBAC и ABAC** (как нужно для твоего case)
2. **Встроенный** (embedded) — не нужны внешние сервисы
3. **Быстрый** — всё в памяти
4. **Гибкий** — легко переходить от простых ролей к сложным политикам

Вот готовый пример для твоего DL мониторинга:

```python
# model.conf
[request_definition]
r = sub, obj, act, status

[policy_definition]
p = sub, obj, act, status, eft

[policy_effect]
e = some(where (p.eft == allow)) && !some(where (p.eft == deny))

[matchers]
m = r.sub == p.sub && r.obj == p.obj && r.act == p.act && r.status == p.status
```

```python
# policy.csv
# Редакторы могут писать только в draft
p, editor, experiment, write, draft, allow
p, editor, experiment, write, completed, deny

# Viewers только читают
p, viewer, experiment, read, *, allow
p, viewer, experiment, write, *, deny

# Admins могут всё
p, admin, *, *, *, allow

# Назначение ролей
g, vasya, editor
g, petya, viewer
```

Хочешь, я покажу полный пример интеграции с FastAPI + SQLAlchemy + Casbin?
<span style="display:none">[^4_10][^4_11][^4_12][^4_13][^4_14][^4_15][^4_16][^4_8][^4_9]</span>

<div align="center">⁂</div>

[^4_1]: https://permify.co/post/open-source-authorization-libraries/

[^4_2]: https://permify.co/post/top-axiomatics-alternatives/

[^4_3]: https://www.permit.io/blog/best-practices-for-authorization-in-python

[^4_4]: https://www.permit.io/blog/fastapi-rbac-full-implementation-tutorial

[^4_5]: https://www.permit.io/blog/implement-authorization-in-fastapi

[^4_6]: https://pypi.org/project/py-abac/0.2.0/

[^4_7]: https://lab.abilian.com/Tech/Python/Useful Libraries/Access control in Python/

[^4_8]: https://www.reddit.com/r/FastAPI/comments/1jn1203/how_do_you_handle_rebac_abac_and_rbac_in_fastapi/

[^4_9]: https://authzed.com/blog/casbin

[^4_10]: https://auth0.com/blog/implementing-rbac-fastapi-auth0-fga/

[^4_11]: https://www.osohq.com/learn/aws-cedar-alternatives-authorization-tools

[^4_12]: https://www.permit.io/tags/implementation-guide

[^4_13]: https://www.reddit.com/r/devops/comments/1hsq81f/any_recommendations_for_open_source_rbac/

[^4_14]: https://github.com/casbin/pycasbin

[^4_15]: https://github.com/pycasbin

[^4_16]: https://slashdot.org/software/p/Casbin/alternatives


---

# Так, мне нужно динамически для разных команд иметь возможность отредактировать, так что правила будут храниться в бд, что под

Вот полная реализация! Ключевые моменты:

## Архитектура[^5_1][^5_2][^5_3]

### 1. **Таблица `casbin_rules`** — хранит все политики

```
| id | ptype | v0        | v1       | v2    | v3           | team_id |
|----|-------|-----------|----------|-------|--------------|---------|
| 1  | p     | editor    | /projects| write | experiment   | team-123|
| 2  | g     | vasya_id  | editor   | NULL  | NULL         | team-123|
| 3  | p     | viewer    | /projects| read  | experiment   | team-123|
```


### 2. **CasbinEnforcerManager** — менеджер для каждой команды

- Создаёт отдельный `enforcer` для каждой команды
- Кеширует enforcers в памяти
- Инвалидирует кеш при изменении политик


### 3. **API endpoints для управления политиками**

```python
# Добавить политику
POST /teams/{team_id}/policies
?subject=editor&obj=/projects&act=write&eft=allow

# Назначить роль пользователю
POST /teams/{team_id}/roles
{"user_identifier": "vasya_id", "role_name": "editor"}

# Получить все политики
GET /teams/{team_id}/policies
```


### 4. **Автоматическая проверка при каждом запросе**

```python
@router.post("/projects/{project_id}/experiments")
async def create_experiment(
    project_id: uuid.UUID,
    # ... проверка Casbin встроена в зависимость!
    _: User = Depends(require_casbin_permission("write", "experiment")),
):
    # Если пользователь не имеет прав → 403
```


## Пример использования

```bash
# 1. Создаем команду "ML Engineers"
POST /teams
{"name": "ML Engineers"}
# Ответ: {"id": "team-123", ...}

# 2. Добавляем политику: редакторы могут писать эксперименты
POST /teams/team-123/policies?subject=editor&obj=/projects&act=write&resource_type=experiment&eft=allow

# 3. Добавляем политику: viewers только читают
POST /teams/team-123/policies?subject=viewer&obj=/projects&act=read&resource_type=experiment&eft=allow

# 4. Назначаем роль Васе
POST /teams/team-123/roles
{"user_identifier": "vasya_id", "role_name": "editor"}

# 5. Теперь Вася может создавать эксперименты!
POST /projects/proj-123/experiments
{"name": "Training v1"}
# ✅ Success

# 6. Но Петя (viewer) не может:
POST /projects/proj-123/experiments  # от пользователя petya_id
# ❌ 403 Forbidden - не имеет прав write на experiment
```


## Преимущества этого подхода

✅ **Динамические политики** — редактируются через API
✅ **Per-team policies** — разные команды имеют разные правила
✅ **Встроенная кеширование** — высокая производительность
✅ **Аудит** — кто и когда изменил политики
✅ **Гибкость** — легко добавить новые правила без перезапуска
✅ **Масштабируемость** — работает с большим количеством политик

Хочешь, я покажу, как добавить **UI для редактирования политик** или **аудит логи**? 🚀
<span style="display:none">[^5_10][^5_11][^5_12][^5_13][^5_14][^5_15][^5_4][^5_5][^5_6][^5_7][^5_8][^5_9]</span>

<div align="center">⁂</div>

[^5_1]: https://pypi.org/project/casbin-async-sqlalchemy-adapter/

[^5_2]: https://pypi.org/project/sqlalchemy-adapter/

[^5_3]: https://casbin.org/docs/api-overview/

[^5_4]: https://hrekov.com/blog/casbin-hierarchical-rbac-maintenance

[^5_5]: https://www.npmjs.com/package/casbin-basic-adapter

[^5_6]: https://github.com/msales/casbin-bun-adapter

[^5_7]: https://casbin.org/docs/adapters/

[^5_8]: https://stackoverflow.com/questions/76386688/how-can-i-link-a-collection-of-users-to-policy-rules-of-a-single-resource-using

[^5_9]: https://casbin.org

[^5_10]: https://casbin.org/ecosystem/

[^5_11]: https://klotzandrew.com/blog/authorization-with-casbin/

[^5_12]: https://pkg.go.dev/github.com/casbin/casbin-pg-adapter

[^5_13]: https://casbin.org/docs/get-started/

[^5_14]: https://github.com/casbin/casbin/issues/596

[^5_15]: https://github.com/casbin/gorm-adapter


---

# Так, какой код тогда надо написать?

Отлично! Теперь у тебя есть **полный рабочий код**. Вот краткий чек-лист:

## ✅ Что нужно сделать

### 1. **Установить зависимости**

```bash
pip install fastapi uvicorn sqlalchemy pycasbin sqlalchemy-adapter
```


### 2. **Запустить приложение**

```bash
python complete_fastapi_app.py
```


### 3. **Открыть Swagger UI**

```
http://localhost:8000/docs
```


***

## 📋 Что включено в код

✅ **Database Models** (User, Team, Project, Experiment, Hypothesis, CasbinRule)
✅ **RBAC с тремя ролями** (admin, editor, viewer)
✅ **Динамические политики в БД** (таблица casbin_rules)
✅ **CasbinEnforcerManager** (менеджер enforcer'ов по командам)
✅ **FastAPI endpoints** для всех операций
✅ **Автоматическая проверка прав** через Depends()
✅ **API для управления политиками** (add, delete, list)
✅ **Инициализация базовых политик** при создании команды

***

## 🔑 Ключевые моменты

**Как работает проверка прав:**

```python
@router.post("/projects/{project_id}/experiments")
async def create_experiment(
    project_id: str,
    experiment: ExperimentCreate,
    current_user: User = Depends(get_current_user),
    # ↓ Вот проверка через Casbin!
    _: User = Depends(require_casbin_permission("write", "experiment")),
    db: Session = Depends(get_db),
):
    # Если пользователь не может писать -> 403 Forbidden
    # Если может -> создаём эксперимент
```

**Как добавить новую политику:**

```python
# 1. Через API
POST /teams/{team_id}/policies
{
    "subject": "reviewer",
    "obj": "/experiments",
    "act": "read",
    "resource_type": "experiment",
    "eft": "allow"
}

# 2. Автоматически - при создании команды загружаются базовые политики
# (см. функцию _init_team_default_policies)
```


***

## 📁 Файлы для скачивания

У тебя есть два основных файла:

1. **`complete_fastapi_app.py`** — Основное приложение (882 строки, готово к запуску)
2. **`SETUP_AND_RUN.md`** — Инструкция с примерами curl'ов

Просто скопируй `complete_fastapi_app.py`, установи зависимости и запусти! 🚀

