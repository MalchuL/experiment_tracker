import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_async_session
from .models import Team, User, team_members, TeamRole
from .auth import current_active_user
from .auth_schemas import TeamCreate, TeamUpdate, TeamRead, TeamMemberAdd, TeamMemberUpdateRole, TeamMemberRead

router = APIRouter(prefix="/teams", tags=["teams"])


async def get_team_with_permission(
    team_id: uuid.UUID,
    session: AsyncSession,
    user: User,
    required_roles: Optional[List[TeamRole]] = None
) -> Team:
    result = await session.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    membership = await session.execute(
        select(team_members).where(
            and_(
                team_members.c.team_id == team_id,
                team_members.c.user_id == user.id
            )
        )
    )
    member_row = membership.first()
    
    if not member_row and team.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    
    if required_roles:
        user_role = TeamRole.OWNER if team.owner_id == user.id else (member_row.role if member_row else None)
        if user_role not in required_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return team


@router.get("", response_model=List[TeamRead])
async def list_teams(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Team).join(team_members, Team.id == team_members.c.team_id).where(team_members.c.user_id == user.id)
    )
    teams = list(result.scalars().all())
    
    teams_with_members = []
    for team in teams:
        members_result = await session.execute(
            select(User, team_members.c.role, team_members.c.joined_at)
            .join(team_members, User.id == team_members.c.user_id)
            .where(team_members.c.team_id == team.id)
        )
        members = [
            TeamMemberRead(
                id=row.User.id,
                email=row.User.email,
                display_name=row.User.display_name,
                role=row.role,
                joined_at=row.joined_at
            )
            for row in members_result
        ]
        teams_with_members.append(TeamRead(
            id=team.id,
            name=team.name,
            description=team.description,
            owner_id=team.owner_id,
            created_at=team.created_at,
            members=members
        ))
    
    return teams_with_members


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(
    data: TeamCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    team = Team(
        name=data.name,
        description=data.description,
        owner_id=user.id
    )
    session.add(team)
    await session.flush()
    
    joined_at = datetime.utcnow()
    await session.execute(
        team_members.insert().values(
            team_id=team.id,
            user_id=user.id,
            role=TeamRole.OWNER,
            joined_at=joined_at
        )
    )
    
    await session.commit()
    await session.refresh(team)
    
    return TeamRead(
        id=team.id,
        name=team.name,
        description=team.description,
        owner_id=team.owner_id,
        created_at=team.created_at,
        members=[TeamMemberRead(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=TeamRole.OWNER,
            joined_at=joined_at
        )]
    )


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    team = await get_team_with_permission(team_id, session, user)
    
    members_result = await session.execute(
        select(User, team_members.c.role, team_members.c.joined_at)
        .join(team_members, User.id == team_members.c.user_id)
        .where(team_members.c.team_id == team_id)
    )
    
    members = []
    for row in members_result:
        members.append(TeamMemberRead(
            id=row.User.id,
            email=row.User.email,
            display_name=row.User.display_name,
            role=row.role,
            joined_at=row.joined_at
        ))
    
    return TeamRead(
        id=team.id,
        name=team.name,
        description=team.description,
        owner_id=team.owner_id,
        created_at=team.created_at,
        members=members
    )


@router.patch("/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: uuid.UUID,
    data: TeamUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    team = await get_team_with_permission(
        team_id, session, user, 
        required_roles=[TeamRole.OWNER, TeamRole.ADMIN]
    )
    
    if data.name is not None:
        team.name = data.name
    if data.description is not None:
        team.description = data.description
    
    await session.commit()
    await session.refresh(team)
    
    members_result = await session.execute(
        select(User, team_members.c.role, team_members.c.joined_at)
        .join(team_members, User.id == team_members.c.user_id)
        .where(team_members.c.team_id == team_id)
    )
    members = [
        TeamMemberRead(
            id=row.User.id,
            email=row.User.email,
            display_name=row.User.display_name,
            role=row.role,
            joined_at=row.joined_at
        )
        for row in members_result
    ]
    
    return TeamRead(
        id=team.id,
        name=team.name,
        description=team.description,
        owner_id=team.owner_id,
        created_at=team.created_at,
        members=members
    )


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    team = await get_team_with_permission(
        team_id, session, user,
        required_roles=[TeamRole.OWNER]
    )
    await session.delete(team)
    await session.commit()


@router.post("/{team_id}/members", response_model=TeamMemberRead)
async def add_team_member(
    team_id: uuid.UUID,
    data: TeamMemberAdd,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    team = await get_team_with_permission(
        team_id, session, user,
        required_roles=[TeamRole.OWNER, TeamRole.ADMIN]
    )
    
    is_owner = team.owner_id == user.id
    if data.role == TeamRole.ADMIN and not is_owner:
        raise HTTPException(status_code=403, detail="Only the owner can assign admin role")
    
    result = await session.execute(select(User).where(User.email == data.email))
    new_member = result.scalar_one_or_none()
    
    if not new_member:
        raise HTTPException(status_code=404, detail="User not found with that email")
    
    existing = await session.execute(
        select(team_members).where(
            and_(
                team_members.c.team_id == team_id,
                team_members.c.user_id == new_member.id
            )
        )
    )
    if existing.first():
        raise HTTPException(status_code=400, detail="User is already a member")
    
    await session.execute(
        team_members.insert().values(
            team_id=team_id,
            user_id=new_member.id,
            role=data.role,
            joined_at=datetime.utcnow()
        )
    )
    await session.commit()
    
    return TeamMemberRead(
        id=new_member.id,
        email=new_member.email,
        display_name=new_member.display_name,
        role=data.role,
        joined_at=datetime.utcnow()
    )


@router.patch("/{team_id}/members/{member_id}", response_model=TeamMemberRead)
async def update_member_role(
    team_id: uuid.UUID,
    member_id: uuid.UUID,
    data: TeamMemberUpdateRole,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    team = await get_team_with_permission(
        team_id, session, user,
        required_roles=[TeamRole.OWNER, TeamRole.ADMIN]
    )
    
    if member_id == team.owner_id:
        raise HTTPException(status_code=400, detail="Cannot change owner's role")
    
    is_owner = team.owner_id == user.id
    if data.role == TeamRole.ADMIN and not is_owner:
        raise HTTPException(status_code=403, detail="Only the owner can assign admin role")
    
    result = await session.execute(
        select(team_members).where(
            and_(
                team_members.c.team_id == team_id,
                team_members.c.user_id == member_id
            )
        )
    )
    member_row = result.first()
    
    if not member_row:
        raise HTTPException(status_code=404, detail="Member not found")
    
    upd_stmt = update(team_members).where(
        and_(
            team_members.c.team_id == team_id,
            team_members.c.user_id == member_id
        )
    ).values(role=data.role)
    await session.execute(upd_stmt)
    await session.commit()
    
    member_user = await session.get(User, member_id)
    if not member_user:
        raise HTTPException(status_code=404, detail="Member not found")
    return TeamMemberRead(
        id=member_id,
        email=member_user.email,
        display_name=member_user.display_name,
        role=data.role,
        joined_at=member_row.joined_at
    )


@router.delete("/{team_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: uuid.UUID,
    member_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    team = await get_team_with_permission(
        team_id, session, user,
        required_roles=[TeamRole.OWNER, TeamRole.ADMIN]
    )
    
    if member_id == team.owner_id:
        raise HTTPException(status_code=400, detail="Cannot remove the owner")
    
    if member_id == user.id:
        raise HTTPException(status_code=400, detail="Use leave endpoint to leave the team")
    
    del_stmt = delete(team_members).where(
        and_(
            team_members.c.team_id == team_id,
            team_members.c.user_id == member_id
        )
    )
    result = await session.execute(del_stmt)
    
    await session.commit()


@router.post("/{team_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_team(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    result = await session.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if team.owner_id == user.id:
        raise HTTPException(status_code=400, detail="Owner cannot leave the team. Transfer ownership or delete the team.")
    
    del_stmt = delete(team_members).where(
        and_(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user.id
        )
    )
    await session.execute(del_stmt)
    
    await session.commit()
