from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status

from openapi import AUTHENTICATION_RESPONSES
from pagination import PaginatedResponse, PaginationParams
from teams.openapi import TEAM_CREATE_RESPONSES, TEAM_UPDATE_RESPONSES, TEAM_NOT_FOUND_RESPONSES
from teams.dependencies import get_team_service
from teams.schemas import TeamCreate, TeamInDB, TeamUpdate
from teams.services import TeamService
from users.models import User
from users.permissions import ensure_team_member_or_mentor, require_mentor

router = APIRouter()

TEAMS_PREFIX = 'Teams'


@router.post(
        '/teams',
        tags=[TEAMS_PREFIX],
        response_model=TeamInDB,
        responses=TEAM_CREATE_RESPONSES,
        status_code=status.HTTP_201_CREATED
)
async def create_team(
    team: TeamCreate,
    service: TeamService = Depends(get_team_service),
    current_user: User = Depends(require_mentor)
):
    return await service.create_team(team, current_user.id)


@router.patch(
        '/teams/{team_id}',
        tags=[TEAMS_PREFIX],
        response_model=TeamUpdate,
        responses={
            **AUTHENTICATION_RESPONSES,
            **TEAM_UPDATE_RESPONSES,
            **TEAM_NOT_FOUND_RESPONSES
        }
)
async def update_team(
    team_id: int,
    update_data: TeamUpdate,
    service: TeamService = Depends(get_team_service),
    current_user: User = Depends(require_mentor)
):
    return await service.update_team(team_id, update_data)


@router.delete(
        '/teams/{team_id}',
        tags=[TEAMS_PREFIX],
        responses={
            **AUTHENTICATION_RESPONSES,
            **TEAM_NOT_FOUND_RESPONSES
        },
        status_code=status.HTTP_204_NO_CONTENT
)
async def delete_team(
    team_id: int,
    service: TeamService = Depends(get_team_service),
    current_user: User = Depends(require_mentor)
):
    await service.delete_team(team_id)


@router.get(
        '/teams/{team_id}',
        tags=[TEAMS_PREFIX],
        response_model=TeamInDB,
        responses={
            **AUTHENTICATION_RESPONSES,
            **TEAM_NOT_FOUND_RESPONSES
        }
)
async def get_team_by_id(
    team_id: int,
    service: TeamService = Depends(get_team_service),
    current_user: User = Depends(ensure_team_member_or_mentor)
):
    return await service.get_team_by_id(team_id)


@router.get(
        '/teams',
        tags=[TEAMS_PREFIX],
        response_model=PaginatedResponse[TeamInDB],
        responses={
            **AUTHENTICATION_RESPONSES,
            **TEAM_NOT_FOUND_RESPONSES
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
        current_user: User = Depends(require_mentor)
):
    teams, total, total_pages = await service.get_all_teams(
        search=search,
        ordering=ordering,
        offset=pagination_params.offset,
        limit=pagination_params.per_page,
        mentor_id=mentor_id
    )
    return PaginatedResponse[TeamInDB](
        items=[team for team in teams if team is not None],
        total=total,
        page=pagination_params.page,
        per_page=pagination_params.per_page,
        total_pages=total_pages
    )
