from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status, Query, UploadFile, Form, File

from auth.services import get_current_user
from openapi import NOT_FOUND_RESPONSE, AUTHENTICATION_RESPONSES
from pagination import PaginatedResponse, PaginationParams
from projects.dependencies import get_project_service
from projects.openapi import PROJECT_CREATE_RESPONSES, PROJECT_CREATE_UPDATE_SCHEMA
from projects.schemas import ProjectInDB, ProjectWithStepsInDB
from projects.services import ProjectService
from users.models import User
from users.permissions import require_mentor
from utils import FileService

router = APIRouter(prefix='/projects')

PROJECT_TAG = 'Projects'


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
        document: UploadFile,
        service: ProjectService = Depends(get_project_service),
        current_user: User = Depends(require_mentor)
):
    """## Create project. Mentor right required"""
    project = await service.create(data, document)
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
        document: Optional[UploadFile] = File(None),
        service: ProjectService = Depends(get_project_service),
        current_user: User = Depends(require_mentor),
):
    """## Update project by id. Mentor rights required"""
    project = await service.update(project_id, data, document)
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
