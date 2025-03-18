import json
from typing import Optional, Tuple

from fastapi import status, HTTPException
from pydantic_core import ValidationError
from sqlalchemy.exc import IntegrityError
from teams.repositories import TeamRepo
from teams.schemas import TeamCreate, TeamInDB, TeamMemberInDB, TeamUpdate
from utils import clean_errors, parse_ordering

class TeamService:
    def __init__(self, repo: TeamRepo):
        self._repo = repo

    async def create_team(self, team: TeamCreate) -> TeamInDB:
        try:
            team = await self._repo.create(team)
            team_model = TeamInDB.model_validate(team)
            team_model.team_members = [TeamMemberInDB.model_validate(member) for member in team.team_members]
            return team_model
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Team with this name already exists'
            )
        
    async def update_team(self, team_id: int, update_data: str) -> TeamInDB:
        try:
            data_dict = json.loads(update_data)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid JSON in user_data field.'
            )
        try:
            update_model = TeamUpdate(**data_dict)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=clean_errors(e.errors())
            )
        except TypeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Data string must be a valid JSON.'
            )
        if 'mentor_id' in update_model.model_fields_set:
            update_model.mentor_id = int(update_model.mentor_id)
        if 'project_id' in update_model.model_fields_set:
            update_model.project_id = int(update_model.project_id)
        team = await self._repo.update_team(team_id, update_model)
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
            search: Optional[str] = None,
            ordering: Optional[str] = None,
            offset: int = 0,
            limit: int = 10
    ) -> Tuple[list[TeamInDB], int, int]:
        order_column, order_direction = parse_ordering(ordering, field_map=self.field_map)
        teams, total = await self._repo.get_all(
            search=search,
            ordering=ordering,
            offset=offset,
            limit=limit,
            order_column=order_column,
            order_direction=order_direction
        )
        teams_models = [TeamInDB.model_validate(team) for team in teams]
        teams_models.team_members = [TeamMemberInDB.model_validate(member) for member in teams.team_members]
        return teams_models, total, offset
    
    