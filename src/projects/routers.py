from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status, Query, UploadFile, Form, File, Body, Path

from auth.services import get_current_user
from openapi import NOT_FOUND_RESPONSE, AUTHENTICATION_RESPONSES, FILE_UPLOAD_RELATED_RESPONSES
from pagination import PaginatedResponse, PaginationParams
from projects.dependencies import get_project_service, get_step_service
from projects.openapi import (
    PROJECT_CREATE_RESPONSES,
    PROJECT_CREATE_UPDATE_SCHEMA,
    STEP_START_RESPONSES,
    STEP_SUBMIT_RESPONSES,
    STEP_ACCEPT_RESPONSES,
    STEP_REJECT_RESPONSES,
    COMMENT_CREATE_RESPONSES
)
from projects.schemas import ProjectInDB, ProjectWithStepsInDB, StepWithRelations, StepCommentInDB
from projects.services import ProjectService, StepService
from users.models import User
from permissions import require_mentor, ensure_team_captain

router = APIRouter(prefix='/projects')

PROJECT_TAG = 'Projects'
STEPS_TAG = 'Steps'


@router.get(
    '/',
    tags=[PROJECT_TAG],
    response_model=PaginatedResponse[ProjectInDB],
    responses={
        **AUTHENTICATION_RESPONSES,
    }
)
async def get_projects(
        pagination_params: PaginationParams = Depends(),
        search: Annotated[Optional[str], Query(
            title='Partial Name Search',
            description='Case-insensitive search on project name.'
        )] = None,
        ordering: Annotated[Optional[str], Query(
            title='Ordering',
            description='Sort field; prefix with "-" for descending order.'
        )] = None,
        service: ProjectService = Depends(get_project_service),
        current_user: User = Depends(get_current_user),
):
    """## Get paginated list of projects. Authenticated user required"""
    projects, total, total_pages = await service.get_all(
        search=search,
        ordering=ordering,
        offset=pagination_params.offset,
        limit=pagination_params.per_page
    )
    return PaginatedResponse(
        items=[ProjectInDB.model_validate(p) for p in projects],
        per_page=pagination_params.per_page,
        page=pagination_params.page,
        total=total,
        total_pages=total_pages
    )


@router.post(
    '/',
    tags=[PROJECT_TAG],
    response_model=ProjectInDB,
    responses={
        **PROJECT_CREATE_RESPONSES,
        **AUTHENTICATION_RESPONSES,
    },
    status_code=status.HTTP_201_CREATED,
    openapi_extra=PROJECT_CREATE_UPDATE_SCHEMA
)
async def create_project(
        data: Annotated[str, Form(..., description='JSON string of user data')],
        document: Annotated[UploadFile, File()],
        service: ProjectService = Depends(get_project_service),
        current_user: User = Depends(require_mentor)
):
    """## Create project. Mentor right required"""
    project = await service.create(project_create=data, document=document)
    return ProjectInDB.model_validate(project)


@router.get(
    '/{project_id}',
    tags=[PROJECT_TAG],
    response_model=ProjectWithStepsInDB,
    responses={
        **NOT_FOUND_RESPONSE,
        **AUTHENTICATION_RESPONSES,
    }
)
async def get_project(
        project_id: int,
        service: ProjectService = Depends(get_project_service),
        current_user: User = Depends(get_current_user),
):
    """## Get project by id. Authenticated user required"""
    project = await service.get_by_id(project_id)
    return ProjectWithStepsInDB.model_validate(project)


@router.patch(
    '/{project_id}',
    tags=[PROJECT_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
    },
    openapi_extra=PROJECT_CREATE_UPDATE_SCHEMA,
)
async def update_project(
        project_id: int,
        data: Annotated[str, Form(description='JSON string of project data')] = None,
        document: Annotated[Optional[UploadFile], File()] = None,
        service: ProjectService = Depends(get_project_service),
        current_user: User = Depends(require_mentor),
):
    """## Update project by id. Mentor rights required"""
    project = await service.update(project_id=project_id, update_data=data, document=document)
    return ProjectInDB.model_validate(project)


@router.delete(
    '/{project_id}',
    tags=[PROJECT_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE
    },
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
        project_id: int,
        service: ProjectService = Depends(get_project_service),
        current_user: User = Depends(require_mentor),
):
    """## Delete project by id. Mentor rights required"""
    return await service.delete(project_id)


@router.get(
    '/{project_id}/steps/{step_num}',
    tags=[STEPS_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
    },
    response_model=StepWithRelations
)
async def get_step(
        project_id: int,
        step_num: Annotated[int, Path(gt=0, lt=16)],
        service: StepService = Depends(get_step_service),
        current_user: User = Depends(get_current_user),
):
    """## Get step. Mentors or members of the team required"""
    step = await service.get_step_or_404(
        project_id=project_id,
        step_num=step_num,
        join_files=True,
        join_comments=True,
        join_attempts=True,
    )
    return StepWithRelations.model_validate(step)


@router.post(
    '/{project_id}/steps/{step_num}/start',
    tags=[STEPS_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
        **STEP_START_RESPONSES,
    },
    response_model=StepWithRelations
)
async def start_step(
        project_id: int,
        step_num: Annotated[int, Path(gt=0, lt=16)],
        service: StepService = Depends(get_step_service),
        user_and_team_id: [User, int] = Depends(ensure_team_captain),
):
    """## Start the work on this step. Team captain role required"""
    step = await service.start_step(
        project_id=project_id,
        step_num=step_num,
        user_team_id=user_and_team_id[1]
    )
    return StepWithRelations.model_validate(step)


@router.post(
    '/{project_id}/steps/{step_num}/set-timer',
    tags=[STEPS_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
    },
    response_model=StepWithRelations
)
async def set_timer(
        project_id: int,
        step_num: Annotated[int, Path(gt=0, lt=16)],
        timer: Annotated[int, Body(gt=0, embed=True, description='Timer value in minutes')],
        service: StepService = Depends(get_step_service),
        current_user: User = Depends(require_mentor),
):
    """## Set new timer value. Mentor rights required

    Updates the last StepAttempt instance's endTimeAt value if the work on this step is in progress.
    """
    step = await service.set_step_timer(
        project_id=project_id,
        step_num=step_num,
        timer=timer
    )
    return StepWithRelations.model_validate(step)


@router.post(
    '/{project_id}/steps/{step_num}/submit_step',
    tags=[STEPS_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
        **FILE_UPLOAD_RELATED_RESPONSES,
        **STEP_SUBMIT_RESPONSES
    },
    response_model=StepWithRelations
)
async def submit_step(
        project_id: int,
        step_num: Annotated[int, Path(gt=0, lt=16)],
        text: Annotated[str, Form(..., max_length=10000)],
        files: Annotated[list[UploadFile], File()] = None,
        service: StepService = Depends(get_step_service),
        user_and_team_id: [User, int] = Depends(ensure_team_captain),
):
    """## Submit the work on the step. Team captain role required"""
    step = await service.submit_step(
        project_id=project_id,
        step_num=step_num,
        text=text,
        files=files if files else [],
        user_team_id=user_and_team_id[1],
    )
    return StepWithRelations.model_validate(step)


@router.post(
    '/{project_id}/steps/{step_num}/accept',
    tags=[STEPS_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
        **STEP_ACCEPT_RESPONSES
    },
    response_model=StepWithRelations
)
async def accept_step(
        project_id: int,
        step_num: Annotated[int, Path(gt=0, lt=16)],
        score: Annotated[int, Body(gt=0, lt=11, embed=True)],
        service: StepService = Depends(get_step_service),
        current_user: User = Depends(require_mentor),
):
    """## Accept the work on the step, set score value. Mentor rights required"""
    result = await service.accept_step(
        project_id=project_id,
        step_num=step_num,
        score=score
    )
    return StepWithRelations.model_validate(result)


@router.post(
    '/{project_id}/steps/{step_num}/reject',
    tags=[STEPS_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
        **STEP_REJECT_RESPONSES,
    },
    response_model=StepWithRelations
)
async def reject_step(
        project_id: int,
        step_num: Annotated[int, Path(gt=0, lt=16)],
        timer: Annotated[Optional[int], Body(gt=0, embed=True, description='Timer value in minutes')] = None,
        service: StepService = Depends(get_step_service),
        current_user: User = Depends(require_mentor),
):
    """## Reject the work on the step. Mentor rights required"""
    step = await service.reject_step(
        project_id=project_id,
        step_num=step_num,
        timer=timer
    )
    return StepWithRelations.model_validate(step)


@router.get(
    '/{project_id}/steps/{step_num}/comments',
    tags=[STEPS_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
    },
    response_model=list[StepCommentInDB]
)
async def get_comments(
        project_id: int,
        step_num: Annotated[int, Path(gt=0, lt=16)],
        service: StepService = Depends(get_step_service),
        current_user: User = Depends(get_current_user),
):
    """## Get comments for the step. Mentors or members of the team required"""
    comments = await service.get_comments(
        project_id=project_id,
        step_num=step_num,
        user=current_user,
    )
    return [StepCommentInDB.model_validate(comment) for comment in comments]


@router.post(
    '/{project_id}/steps/{step_num}/comments',
    tags=[STEPS_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
        **FILE_UPLOAD_RELATED_RESPONSES,
        **COMMENT_CREATE_RESPONSES
    },
    response_model=StepCommentInDB,
    status_code=status.HTTP_201_CREATED
)
async def create_comment(
        project_id: int,
        step_num: Annotated[int, Path(gt=0, lt=16)],
        text: Annotated[str, Form(..., max_length=500)],
        files: Annotated[list[UploadFile], File()] = None,
        service: StepService = Depends(get_step_service),
        current_user: User = Depends(get_current_user),
):
    """## Create a comment. Mentors or members of the team required"""
    comment = await service.create_comment(
        project_id=project_id,
        step_num=step_num,
        text=text,
        files=files,
        user=current_user
    )
    return StepCommentInDB.model_validate(comment)


@router.delete(
    '/{project_id}/steps/{step_num}/comments/{comment_id}',
    tags=[STEPS_TAG],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
    },
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
        project_id: int,
        step_num: Annotated[int, Path(gt=0, lt=16)],
        comment_id: int,
        service: StepService = Depends(get_step_service),
        current_user: User = Depends(get_current_user),
):
    """## Delete a comment. Mentors or authors of the comment required"""
    await service.delete_comment(
        project_id=project_id,
        step_num=step_num,
        comment_id=comment_id,
        user=current_user
    )
