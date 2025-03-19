from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from openapi import AUTHENTICATION_RESPONSES
from teams.dependencies import get_team_service
from teams.services import TeamService
from teams.schemas import TeamCreateUpdate, TeamInDB
from pagination import PaginatedResponse, PaginationParams
from teams import openapi
from users.models import User
from users.permissions import require_mentor

router = APIRouter()

TEAMS_PREFIX = 'Teams'


@router.post(
        '/teams',
        tags=[TEAMS_PREFIX],
        response_model=TeamInDB,
        responses=openapi.TEAM_CREATE_RESPONSES,
        openapi_extra=openapi.TEAM_CREATE_SCHEMA
)
async def create_team(
    team: TeamCreateUpdate,
    service: TeamService = Depends(get_team_service),
    current_user: User = Depends(require_mentor)
):
    return await service.create_team(team, current_user.id)


@router.patch(
        '/teams/{team_id}',
        tags=[TEAMS_PREFIX],
        response_model=TeamCreateUpdate,
        responses={
            **AUTHENTICATION_RESPONSES,
            **openapi.TEAM_UPDATE_RESPONSES,
            **openapi.TEAM_NOT_FOUND_RESPONSES
        }
)
async def update_team(
    team_id: int,
    update_data: TeamCreateUpdate = None,
    service: TeamService = Depends(get_team_service),
    current_user: User = Depends(require_mentor)
):
    return await service.update_team(team_id, update_data, current_user.id)


@router.delete(
        '/teams/{team_id}',
        tags=[TEAMS_PREFIX],
        responses={
            **AUTHENTICATION_RESPONSES,
            **openapi.TEAM_DELETE_RESPONSES,
            **openapi.TEAM_NOT_FOUND_RESPONSES
        },
        status_code=status.HTTP_204_NO_CONTENT
)
async def delete_team(
    team_id: int,
    service: TeamService = Depends(get_team_service)
):
    await service.delete_team(team_id)


@router.get(
        '/teams/{team_id}',
        tags=[TEAMS_PREFIX],
        response_model=TeamInDB,
        responses={
            **AUTHENTICATION_RESPONSES,
            **openapi.TEAM_GET_RESPONSES,
            **openapi.TEAM_NOT_FOUND_RESPONSES
        }
)
async def get_team_by_id(
    team_id: int,
    service: TeamService = Depends(get_team_service)
):
    return await service.get_team_by_id(team_id)


@router.get(
        '/teams',
        tags=[TEAMS_PREFIX],
        response_model=PaginatedResponse[TeamInDB],
        responses={
            **AUTHENTICATION_RESPONSES,
            **openapi.TEAM_GET_ALL_RESPONSES,
            **openapi.TEAM_NOT_FOUND_RESPONSES
        }
)
async def get_all_teams(
        pagination_params: PaginationParams = Depends(),
        search: Annotated[Optional[str], Query(
            title='Partial Name Search',
            description='Case-insensitive search on team name.'
        )] = None,
        ordering: Annotated[Optional[str], Query(
            title='Ordering',
            description='Sort field; prefix with "-" for descending order.'
        )] = None,
        mentor_id: Annotated[Optional[int], Query(
            title='Mentor ID',
            description='Filter teams by mentor ID.'
        )] = None,
        service: TeamService = Depends(get_team_service),
):
    return await service.get_all_teams(
        search=search,
        ordering=ordering,
        offset=pagination_params.offset,
        limit=pagination_params.limit,
        mentor_id=mentor_id
    )
