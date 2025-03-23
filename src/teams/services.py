from math import ceil
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from exceptions import NotFoundError
from teams.repositories import TeamRepo
from teams.schemas import TeamCreate, TeamInDB, TeamMemberInDB, TeamUpdate, TeamMemberCreateUpdate
from utils import create_field_map_for_model, parse_ordering


class TeamService:
    field_map: dict = create_field_map_for_model(TeamInDB)

    def __init__(self, repo: TeamRepo):
        self._repo = repo

    async def create_team(self, team: TeamCreate, mentor_id: int) -> TeamInDB:
        try:
            team_data = team.model_dump()
            team = TeamCreate(**team_data)
            team_db = await self._repo.create(team_data=team, mentor_id=mentor_id)
            team_model = TeamInDB.model_validate(team_db)
            team_model.team_members = [TeamMemberInDB.model_validate(member) for member in team_db.team_members]
            return team_model
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Team with this name already exists or the mentor ID is missing from the response'
            )

    async def update_team(
            self,
            team_id: int,
            update_data: TeamUpdate,
    ) -> TeamUpdate:
        try:
            if 'project_id' in update_data.model_fields_set and update_data.project_id is not None:
                update_data.project_id = int(update_data.project_id)
            team_members = update_data.model_dump(exclude_unset=True).pop('team_members', None)
            team = await self._repo.update_team(team_id, update_data.model_dump(exclude_unset=True))
            team_model = TeamUpdate.model_validate(team)
            if team_members:
                team_model.team_members = [TeamMemberCreateUpdate.model_validate(member) for member in team_members]
            return team_model
        except NotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team not found'
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
    ) -> Tuple[list[TeamInDB], int, int]:
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
