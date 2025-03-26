from typing import Literal, Optional, Sequence, Tuple

from sqlalchemy import (ColumnElement, Select, asc, delete, desc, func, or_,
                        select)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from exceptions import NotFoundError
from teams.models import Team, TeamMember
from teams.schemas import TeamCreate, TeamMemberCreateUpdate


class TeamRepo:
    def __init__(self, db: AsyncSession):
        self._db = db

    @staticmethod
    def _add_team_joins(
            query: Select,
            mentor_join: bool = False,
            project_join: bool = False,
            team_members_join: bool = False,
    ) -> Select:
        if mentor_join:
            query = query.options(joinedload(Team.mentor))
        if project_join:
            query = query.options(joinedload(Team.project))
        if team_members_join:
            query = query.options(joinedload(Team.team_members))
        return query

    async def get_all(
        self,
        *,
        search: Optional[str] = None,
        mentor_id: Optional[int] = None,
        project_id: Optional[int] = None,
        project_join: bool = False,
        mentor_join: bool = False,
        team_members_join: bool = False,
        order_column: Literal['id', 'name', 'created_at', 'mentor_id', 'project_id'] = 'id',
        order_direction: Literal['ASC', 'DESC'] = 'ASC',
        offset: int = 0,
        limit: int = 10,
    ) -> Tuple[Sequence[Team], int]:
        base_query = select(Team)

        filters: list[ColumnElement[bool]] = []
        if search:
            filters.append(Team.name.ilike(f'%{search}%'))
        if mentor_id:
            filters.append(Team.mentor_id == mentor_id)

        if project_id is not None:
            filters.append(Team.project_id == project_id)

        if filters:
            base_query = base_query.where(*filters)

        count_query = select(func.count(Team.id))
        if filters:
            count_query = count_query.where(*filters)

        count_result = await self._db.execute(count_query)
        total = count_result.scalar() or 0

        column = getattr(Team, order_column, None)
        if column is not None:
            if order_direction == 'ASC':
                base_query = base_query.order_by(asc(column))
            else:
                base_query = base_query.order_by(desc(column))

        base_query = self._add_team_joins(base_query, mentor_join, project_join, team_members_join)

        base_query = base_query.offset(offset).limit(limit)

        result = await self._db.execute(base_query)
        return result.scalars().all(), total

    async def get_by_id(
            self,
            team_id: int,
            *,
            mentor_join: bool = False,
            project_join: bool = False,
            team_members_join: bool = False,
    ) -> Optional[Team]:
        base_query = select(Team).where(Team.id == team_id)
        base_query = self._add_team_joins(base_query, mentor_join, project_join, team_members_join)
        result = await self._db.execute(base_query)
        return result.scalar_one_or_none()

    async def get_by_project_or_mentor(
            self,
            project_id: Optional[int] = None,
            mentor_id: Optional[int] = None,
            project_join: bool = False,
            mentor_join: bool = False,
            team_members_join: bool = False,
    ) -> Optional[Team]:
        """
        Получить команду по проекту или ментору. Если не указать ни один из параметров, то вернется None.
        """
        conditions: list[ColumnElement[bool]] = []

        if project_id is not None:
            conditions.append(Team.project_id == project_id)

        if mentor_id is not None:
            conditions.append(Team.mentor_id == mentor_id)

        if not conditions:
            return None

        query = select(Team).where(or_(*conditions))

        query = self._add_team_joins(query, mentor_join, project_join, team_members_join)

        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def create(
            self,
            team_data: TeamCreate,
    ) -> Team:
        team = Team(**team_data.model_dump(exclude={'team_members'}))
        self._db.add(team)
        await self._db.flush()

        if team_data.team_members:
            member_repo = TeamMemberRepo(self._db)
            members_sequence = (
                team_data.team_members if isinstance(team_data.team_members, Sequence) else [team_data.team_members]
            )
            await member_repo.create_several_team_members(members_sequence)
        await self._db.refresh(team, attribute_names=['mentor', 'project', 'team_members'])
        return team

    async def update_team(
            self,
            team_id: int,
            update_data: dict,
    ) -> Team:
        team = await self.get_by_id(team_id)
        if not team:
            raise NotFoundError('Team not found')
        for key, value in update_data.items():
            setattr(team, key, value)
        self._db.add(team)
        await self._db.flush()
        if 'team_members' in update_data:
            await self._update_team_members(update_data.pop('team_members'))
        await self._db.refresh(team)
        return team

    async def delete_team(
            self,
            team_id: int,
    ) -> None:
        await self._db.execute(delete(Team).where(Team.id == team_id))
        await self._db.commit()

    async def _update_team_members(self, members: list[dict]):
        member_repo = TeamMemberRepo(self._db)
        for member in members:
            await member_repo.update_team_member(member['id'], member)


class TeamMemberRepo:
    def __init__(self, db: AsyncSession):
        self._db = db

    @staticmethod
    def _add_team_member_joins(
            query: Select,
            team_join: bool = False,
            participant_join: bool = False,
    ) -> Select:
        if team_join:
            query = query.options(joinedload(TeamMember.team))
        if participant_join:
            query = query.options(joinedload(TeamMember.participant))
        return query

    async def get_all(
            self,
            team_id: int,
            *,
            team_join: bool = False,
            participant_join: bool = False,
            search: Optional[str] = None,
            order_column: Literal['id', 'participant_id', 'team_id', 'created_at'] = 'id',
            order_direction: Literal['ASC', 'DESC'] = 'ASC',
            offset: int = 0,
            limit: int = 10,
    ) -> Tuple[Sequence[TeamMember], int]:
        base_query = select(TeamMember)

        filters: list[ColumnElement[bool]] = []
        if search:
            filters.append(TeamMember.role_name.ilike(f'%{search}%'))

        if team_id:
            filters.append(TeamMember.team_id == team_id)

        if filters:
            base_query = base_query.where(*filters)

        count_query = select(func.count(TeamMember.id))
        if filters:
            count_query = count_query.where(*filters)

        count_result = await self._db.execute(count_query)
        total = count_result.scalar() or 0

        column = getattr(TeamMember, order_column, None)
        if column is not None:
            if order_direction == 'ASC':
                base_query = base_query.order_by(asc(column))
            else:
                base_query = base_query.order_by(desc(column))

        base_query = self._add_team_member_joins(base_query, team_join, participant_join)
        base_query = base_query.offset(offset).limit(limit)

        result = await self._db.execute(base_query)
        return result.scalars().all(), total

    async def get_by_id(
            self,
            team_member_id: int,
            *,
            team_join: bool = False,
            participant_join: bool = False,
    ) -> Optional[TeamMember]:
        base_query = select(TeamMember).where(TeamMember.id == team_member_id)
        base_query = self._add_team_member_joins(base_query, team_join, participant_join)
        result = await self._db.execute(base_query)
        return result.scalar_one_or_none()

    async def get_by_team(
        self,
        team_id: int,
        *,
        team_join: bool = False,
        participant_join: bool = False,
    ) -> Sequence[TeamMember]:
        base_query = select(TeamMember).where(TeamMember.team_id == team_id)
        base_query = self._add_team_member_joins(base_query, team_join, participant_join)
        result = await self._db.execute(base_query)
        return result.scalars().all()

    async def get_by_participant(
        self,
        participant_id: int,
        *,
        team_join: bool = False,
        participant_join: bool = False,
    ) -> Sequence[TeamMember]:
        base_query = select(TeamMember).where(TeamMember.participant_id == participant_id)
        base_query = self._add_team_member_joins(base_query, team_join, participant_join)
        result = await self._db.execute(base_query)
        return result.scalars().all()

    async def get_by_user_id(
        self,
        user_id: int,
    ) -> Optional[TeamMember]:
        base_query = select(TeamMember).where(TeamMember.participant_id == user_id)
        result = await self._db.execute(base_query)
        return result.scalar_one_or_none()

    async def create_several_team_members(
            self,
            team_members_data: Sequence[TeamMemberCreateUpdate],
    ) -> Sequence[TeamMember]:
        async with self._db.begin():
            team_members = [TeamMember(**member.model_dump()) for member in team_members_data]
            self._db.add_all(team_members)
            await self._db.flush()
            await self._db.refresh(team_members, attribute_names=['team', 'participant'])
        return team_members

    async def update_team_member(
            self,
            team_member_id: int,
            update_data: dict,
    ) -> TeamMember:
        async with self._db.begin():
            team_member = await self.get_by_id(team_member_id)
            if not team_member:
                raise NotFoundError('Team member not found')
            for key, value in update_data.items():
                setattr(team_member, key, value)
            self._db.add(team_member)
            await self._db.commit()
            await self._db.refresh(team_member)
        return team_member

    async def delete_team_member(
            self,
            team_member: TeamMember,
    ) -> None:
        await self._db.execute(delete(TeamMember).where(TeamMember.id == team_member.id))
        await self._db.commit()
