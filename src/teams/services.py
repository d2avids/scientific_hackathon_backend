from math import ceil
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from exceptions import AlreadyExistsError, NotFoundError
from teams.repositories import TeamMemberRepo, TeamRepo
from teams.schemas import TeamCreate, TeamInDB, TeamMemberInDB, TeamUpdate, TeamMemberCreateUpdate
from users.models import User
from utils import create_field_map_for_model, parse_ordering


class TeamService:
    field_map: dict = create_field_map_for_model(TeamInDB)

    def __init__(self, repo: TeamRepo):
        self._repo = repo

    async def create_team(self, team: TeamCreate, mentor_id: int) -> TeamInDB:
        try:
            team_db = await self._repo.create(team_data=team, mentor_id=mentor_id)
            team_model = TeamInDB.model_validate(team_db)
            team_model.team_members = [TeamMemberInDB.model_validate(member) for member in team_db.team_members]
            return team_model
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Integrity error. Check the data for correctness.'
            )

    async def update_team(
            self,
            team_id: int,
            update_data: TeamUpdate,
    ) -> TeamUpdate:
        try:
            update_dict = update_data.model_dump(exclude_unset=True)
            team_members = update_dict.pop('team_members', None)

            if team_members:
                if len(team_members) > 10:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='The maximum number of team members is 10.'
                    )
                team_members = [TeamMemberCreateUpdate.model_validate(member) for member in team_members]

            update_data = TeamUpdate.model_validate(update_dict)

            team = await self._repo.update_team(
                team_id=team_id,
                update_data=update_data.model_dump(exclude_unset=True),
                team_members=team_members
            )
            team_model = TeamUpdate.model_validate(team)
            return team_model
        except NotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team or team members not found'
            )
        except AlreadyExistsError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Team member is already in a team'
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Integrity error. Check the data for correctness.'
            )

    async def delete_team(self, team_id: int) -> None:
        team = await self._repo.get_by_id(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team not found'
            )
        await self._repo.delete_team(team_id)

    async def get_team_by_id(self, team_id: int) -> TeamInDB:
        team = await self._repo.get_by_id(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team not found'
            )
        team_model = TeamInDB.model_validate(team)
        team_model.team_members = [TeamMemberInDB.model_validate(member) for member in team.team_members]
        return team_model

    async def get_all_teams(
            self,
            *,
            search: Optional[str] = None,
            ordering: Optional[str] = None,
            mentor_id: Optional[int] = None,
            offset: int = 0,
            limit: int = 10,
    ) -> tuple[list[TeamInDB], int, int]:
        order_column, order_direction = parse_ordering(ordering, field_map=self.field_map)
        if order_column not in self.field_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid ordering column'
            )
        teams, total = await self._repo.get_all(
            search=search,
            offset=offset,
            limit=limit,
            order_column=self.field_map[order_column],
            order_direction=order_direction,
            mentor_id=mentor_id
        )
        teams_models: list[TeamInDB] = []
        for team in teams:
            team_model = TeamInDB.model_validate(team)
            team_model.team_members = [TeamMemberInDB.model_validate(member) for member in team.team_members]
            teams_models.append(team_model)
        total_pages = ceil(total / limit) if total > 0 else 1
        return teams_models, total, total_pages

    async def delete_team_project(self, team_id: int) -> None:
        team = await self._repo.get_by_id(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team not found'
            )
        await self._repo.delete_team_project(team_id)


class TeamMemberService:
    def __init__(self, repo: TeamMemberRepo):
        self._repo = repo

    async def create_several_team_members(
            self,
            team_id: int,
            members: list[TeamMemberCreateUpdate],
    ) -> list[TeamMemberInDB]:
        check_team = await self._repo.get_by_team(team_id)
        if not check_team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team not found'
            )
        if len(members) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='The maximum number of team members is 10.'
            )

        has_captain_in_entry_data = any(
            member.role_name and member.role_name.strip().lower().startswith('капитан')
            for member in members
        )
        if has_captain_in_entry_data:
            check_captain_name = await self._repo.get_team_by_member_rolename('капитан', team_id)
            if check_captain_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Captain role name is reserved for the team. '
                    'To change the captain, use the update method after creating the instance.'
                )
        try:
            member_db = await self._repo.create_several_team_members(
                team_members_data=members,
                team_id=team_id,
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Integrity error. Check the data for correctness.'
            )
        return [TeamMemberInDB.model_validate(member) for member in member_db]

    async def change_team_member_role(
            self,
            team_id: int,
            team_member_id: int,
            role_name: str,
            current_user: User
    ) -> TeamMemberInDB:
        team_member = await self._repo.get_team_member_by_id(team_member_id)
        if not team_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team member instance not found'
            )
        if team_member.team_id != team_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team member not found'
            )
        if (
            not current_user.is_mentor
            and ((role_name.lower().startswith('капитан') or team_member.participant_id == current_user.participant.id))
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Only mentors can change the captain role'
            )
        await self._repo.update_team_member(team_id, team_member_id, {'role_name': role_name})
        return TeamMemberInDB.model_validate(team_member)

    async def delete_team_member(self, team_id: int, team_member_id: int) -> None:
        team_member = await self._repo.get_team_member_by_id(team_member_id)
        if not team_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team member instance not found'
            )
        if team_member.team_id != team_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team member not found'
            )
        await self._repo.delete_team_member(team_member_id, team_id)
