from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status

from openapi import AUTHENTICATION_RESPONSES, NOT_FOUND_RESPONSE
from pagination import PaginatedResponse, PaginationParams
from permissions import ensure_team_member_or_mentor, require_mentor, ensure_team_captain_or_mentor
from teams.dependencies import get_team_member_service, get_team_service
from teams.openapi import TEAM_CREATE_RESPONSES, TEAM_UPDATE_RESPONSES
from teams.schemas import TeamCreate, TeamInDB, TeamMemberCreateUpdate, TeamMemberInDB, TeamUpdate
from teams.services import TeamMemberService, TeamService
from users.models import User

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
    """
    ## Create a team. Only mentors can create teams.

    ### Request
    ```json
    {
    "name": "string", # required
    "teamMembers": [ # optional
        {
        "participantId": 0, # required if teamMembers is provided
        "roleName": "string" # optional
        }
    ]
    }
    ```
    """
    return await service.create_team(team, current_user.mentor.id)


@router.patch(
    '/teams/{team_id}',
    tags=[TEAMS_PREFIX],
    response_model=TeamUpdate,
    responses={
        **AUTHENTICATION_RESPONSES,
        **TEAM_UPDATE_RESPONSES,
        **NOT_FOUND_RESPONSE
    }
)
async def update_team(
        team_id: int,
        update_data: TeamUpdate,
        service: TeamService = Depends(get_team_service),
        current_user: User = Depends(require_mentor)
):
    """
    ## Update a team. Only mentors can update teams.

    All fields are optional.
    This endpoint can be used to appoint a team captain.
    """
    return await service.update_team(team_id, update_data)


@router.delete(
    '/teams/{team_id}',
    tags=[TEAMS_PREFIX],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE
    },
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_team(
        team_id: int,
        service: TeamService = Depends(get_team_service),
        current_user: User = Depends(require_mentor)
):
    """
    ## Delete a team. Only mentors can delete teams.
    """
    await service.delete_team(team_id)


@router.get(
    '/teams/{team_id}',
    tags=[TEAMS_PREFIX],
    response_model=TeamInDB,
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE
    }
)
async def get_team_by_id(
        team_id: int,
        service: TeamService = Depends(get_team_service),
        current_user: User = Depends(ensure_team_member_or_mentor)
):
    """
    ## Get a team by ID.
    Allowed for mentors and team members.
    """
    return await service.get_team_by_id(team_id)


@router.get(
    '/teams',
    tags=[TEAMS_PREFIX],
    response_model=PaginatedResponse[TeamInDB],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE
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
    """
    ## Get all teams.
    Allowed for mentors only.
    """
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


@router.post(
    '/teams/{team_id}/members',
    tags=[TEAMS_PREFIX],
    response_model=list[TeamMemberInDB],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE
    },
    status_code=status.HTTP_201_CREATED
)
async def add_team_members(
        team_id: int,
        members: list[TeamMemberCreateUpdate],
        service: TeamMemberService = Depends(get_team_member_service),
        current_user: User = Depends(require_mentor)
):
    """
    ## Add team members to a team.
    Allowed for mentors only.

    ### Request
    ```json
    [
        {
        "participantId": 0, # required
        "roleName": "string" # optional
        }
    ]
    """
    return await service.create_several_team_members(team_id, members)


@router.post(
    '/teams/{team_id}/members/{team_member_id}/role_name',
    tags=[TEAMS_PREFIX],
    response_model=TeamMemberInDB,
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE
    }
)
async def change_team_member_role(
        team_id: int,
        team_member_id: int,
        role_name: str,
        service: TeamMemberService = Depends(get_team_member_service),
        current_user: User = Depends(ensure_team_captain_or_mentor)
):
    """
    ## Change a team member's role.
    Allowed for captains and mentors. This endpoint can be used by mentors to appoint a team captain.
    """
    return await service.change_team_member_role(team_id, team_member_id, role_name, current_user)


@router.delete(
    '/teams/{team_id}/members/{team_member_id}',
    tags=[TEAMS_PREFIX],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE
    },
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_team_member(
        team_id: int,
        team_member_id: int,
        service: TeamMemberService = Depends(get_team_member_service),
        current_user: User = Depends(require_mentor)
):
    """
    ## Delete a team member.
    Allowed for mentors only.
    """
    await service.delete_team_member(team_id, team_member_id)
