from typing import Literal, Optional, Sequence

from sqlalchemy import (ColumnElement, Select, asc, delete, desc, func, or_,
                        select, update, and_)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from exceptions import NotFoundError, AlreadyExistsError
from teams.models import Team, TeamMember
from teams.schemas import TeamCreate, TeamMemberCreateUpdate
from users.models import User, Participant


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
            query = query.options(
                joinedload(Team.team_members)
                .joinedload(TeamMember.participant)
                .joinedload(Participant.user)
            )
        return query

    async def get_all(
        self,
        *,
        search: Optional[str] = None,
        mentor_id: Optional[int] = None,
        project_id: Optional[int] = None,
        project_join: bool = False,
        mentor_join: bool = False,
        team_members_join: bool = True,
        order_column: Literal['id', 'name', 'created_at', 'mentor_id', 'project_id'] = 'id',
        order_direction: Literal['ASC', 'DESC'] = 'ASC',
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[Sequence[Team], int]:
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
        return result.scalars().unique().all(), total

    async def get_by_id(
            self,
            team_id: int,
            *,
            mentor_join: bool = False,
            project_join: bool = False,
            team_members_join: bool = True,
    ) -> Optional[Team]:
        base_query = select(Team).where(Team.id == team_id)
        base_query = self._add_team_joins(base_query, mentor_join, project_join, team_members_join)
        result = await self._db.execute(base_query)
        return result.scalars().unique().one_or_none()

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

    async def get_by_role_name(
            self,
            name: str,
            team_id: int,
    ) -> Optional[Team]:
        base_query = select(Team).where(Team.id == team_id)
        base_query = base_query.where(Team.team_members.any(TeamMember.role_name.ilike(f'%{name}%')))
        base_query = self._add_team_joins(base_query, team_members_join=True)
        result = await self._db.execute(base_query)
        return result.scalars().unique().one_or_none()

    async def create(
            self,
            team_data: TeamCreate,
            mentor_id: int,
    ) -> Team:

        team = Team(**team_data.model_dump(exclude={'team_members'}))
        team.mentor_id = mentor_id
        self._db.add(team)
        await self._db.flush()
        await self._db.refresh(team, attribute_names=['mentor', 'project', 'team_members'])
        if team_data.team_members:
            member_repo = TeamMemberRepo(self._db)
            members_sequence = (
                team_data.team_members if isinstance(team_data.team_members, Sequence) else [team_data.team_members]
            )
            await member_repo.create_several_team_members(members_sequence, team.id, commit=False)
        await self._db.commit()
        await self._db.refresh(team, attribute_names=['mentor', 'project', 'team_members'])
        return team

    async def update_team(
            self,
            team_id: int,
            update_data: dict,
            team_members: Optional[list[dict]] = None
    ) -> Team:
        team_members = update_data.pop('team_members', None)
        team = await self.get_by_id(team_id)
        if not team:
            raise NotFoundError('Team not found')

        for key, value in update_data.items():
            setattr(team, key, value)
        self._db.add(team)
        await self._db.flush()
        if team_members is not None:
            members_data = [member.model_dump() if hasattr(member, 'model_dump') else member for member in team_members]
            await self.update_team_members(team_id, members_data, commit=False)
        await self._db.commit()
        await self._db.refresh(team, attribute_names=['mentor', 'project', 'team_members'])
        return team

    async def delete_team(
            self,
            team_id: int,
    ) -> None:
        await self._db.execute(delete(Team).where(Team.id == team_id))
        await self._db.commit()

    async def update_team_members(self, team_id: int, members_data: list[dict], commit: bool = True):
        member_repo = TeamMemberRepo(self._db)
        updated_members = []
        for member_data in members_data:
            member = await member_repo.get_team_member_by_participant_id(member_data['participant_id'])
            if member:
                updated_member = await member_repo.update_team_member(
                    team_id=team_id,
                    team_member_id=member.id,
                    update_data=member_data,
                    commit=False
                )
                updated_members.append(updated_member)
        if commit:
            await self._db.commit()
            for member in updated_members:
                await self._db.refresh(member)

    async def delete_team_project(self, team_id: int) -> None:
        await self._db.execute(update(Team).where(Team.id == team_id).values(project_id=None))
        await self._db.commit()


class TeamMemberRepo:
    DEFAULT_ROLE_NAME = 'Участник'

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
    ) -> tuple[Sequence[TeamMember], int]:
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

    async def get_team_member_by_id(
            self,
            team_member_id: int,
            *,
            team_join: bool = False,
            participant_join: bool = False,
    ) -> Optional[TeamMember]:
        base_query = select(TeamMember).where(TeamMember.id == team_member_id)
        base_query = self._add_team_member_joins(base_query, team_join, participant_join)
        result = await self._db.execute(base_query)
        return result.scalars().unique().one_or_none()

    async def get_team_member_by_participant_id(
            self,
            participant_id: int,
    ) -> Optional[TeamMember]:
        base_query = select(TeamMember).where(TeamMember.participant_id == participant_id)
        result = await self._db.execute(base_query)
        return result.scalars().unique().one_or_none()

    async def get_by_user(
            self,
            user: User,
    ) -> Optional[TeamMember]:
        base_query = select(TeamMember).where(TeamMember.participant_id == user.participant.id)
        result = await self._db.execute(base_query)
        return result.scalars().unique().one_or_none()

    async def create_several_team_members(
            self,
            team_members_data: Sequence[TeamMemberCreateUpdate],
            team_id: int,
            commit: bool = True,
    ) -> list[TeamMember]:
        team_members = []
        for member in team_members_data:
            member_data = member.model_dump()
            member_db = TeamMember(**member_data)
            member_db.team_id = team_id
            team_members.append(member_db)
        self._db.add_all(team_members)
        await self._db.flush()
        for member_db in team_members:
            await self._db.refresh(member_db, attribute_names=['team', 'participant'])
        if commit:
            await self._db.commit()
        return team_members

    async def update_team_member(
            self,
            team_id: int,
            team_member_id: int,
            update_data: dict,
            commit: bool = True,
    ) -> TeamMember:
        team_member = await self.get_team_member_by_id(team_member_id)
        if not team_member:
            raise NotFoundError('Team member not found')
        if team_member.team_id and team_member.team_id != team_id:
            raise AlreadyExistsError('Team member is already on another team')
        for key, value in update_data.items():
            if key == 'role_name' and value.lower().startswith('капитан'):
                await self.update_captain_role(team_id, self.DEFAULT_ROLE_NAME, commit=False)
            setattr(team_member, key, value)
        self._db.add(team_member)
        if commit:
            await self._db.commit()
            await self._db.refresh(team_member)
        return team_member

    async def delete_team_member(
            self,
            team_member_id: int,
            team_id: int,
    ) -> None:
        await self._db.execute(delete(TeamMember).where(TeamMember.id == team_member_id, TeamMember.team_id == team_id))
        await self._db.commit()

    async def get_team_by_member_rolename(
        self,
        name: str,
        team_id: int,
    ) -> Optional[TeamMember]:
        base_query = select(TeamMember).where(TeamMember.role_name.ilike(f'%{name}%'), TeamMember.team_id == team_id)
        result = await self._db.execute(base_query)
        return result.scalars().unique().one_or_none()

    async def update_captain_role(self, team_id: int, default_role: str, commit: bool = True) -> None:
        query = (
            update(TeamMember)
            .where(
                and_(
                    TeamMember.team_id == team_id,
                    func.lower(TeamMember.role_name) == 'капитан'
                )
            )
            .values(role_name=default_role)
        )
        result = await self._db.execute(query)
        if result.rowcount == 0:
            pass
        else:
            if commit:
                await self._db.commit()

    async def get_by_name(
            self,
            name: str,
    ) -> Optional[TeamMember]:
        base_query = select(TeamMember).where(TeamMember.role_name.ilike(f'%{name}%'))
        result = await self._db.execute(base_query)
        return result.scalars().unique().one_or_none()
