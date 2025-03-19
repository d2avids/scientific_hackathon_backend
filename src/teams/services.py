from typing import Optional, Tuple

from fastapi import status, HTTPException
from sqlalchemy.exc import IntegrityError
from teams.repositories import TeamRepo
from teams.schemas import TeamCreateUpdate, TeamInDB, TeamMemberInDB
from utils import parse_ordering, create_field_map_for_model


class TeamService:
    field_map: dict = create_field_map_for_model(TeamInDB)

    def __init__(self, repo: TeamRepo):
        self._repo = repo

    async def create_team(self, team: TeamCreateUpdate, mentor_id: int) -> TeamInDB:
        try:

            team_data = team.model_dump()
            team_data['mentor_id'] = mentor_id
            team = TeamCreateUpdate(**team_data)

            team = await self._repo.create(team)
            team_model = TeamInDB.model_validate(team)
            team_model.team_members = [TeamMemberInDB.model_validate(member) for member in team.team_members]
            return team_model
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Team with this name already exists'
            )

    async def update_team(self, team_id: int, update_data: TeamCreateUpdate, mentor_id: int) -> TeamInDB:
        update_data.mentor_id = int(mentor_id)
        if 'project_id' in update_data.model_fields_set:
            update_data.project_id = int(update_data.project_id)
        team = await self._repo.update_team(team_id, update_data)
        team_model = TeamInDB.model_validate(team)
        team_model.team_members = [TeamMemberInDB.model_validate(member) for member in team.team_members]
        return team_model

    async def delete_team(self, team_id: int) -> None:
        await self._repo.delete_team(team_id)

    async def get_team_by_id(self, team_id: int) -> TeamInDB:
        team = await self._repo.get_by_id(team_id)
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
        teams, total = await self._repo.get_all(
            search=search,
            ordering=ordering,
            offset=offset,
            limit=limit,
            order_column=order_column,
            order_direction=order_direction,
            mentor_id=mentor_id
        )
        teams_models: list[TeamInDB] = []
        for team in teams:
            team_model = TeamInDB.model_validate(team)
            team_model.team_members = [TeamMemberInDB.model_validate(member) for member in team.team_members]
            teams_models.append(team_model)
        return teams_models, total, offset
