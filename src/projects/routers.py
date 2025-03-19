from typing import Annotated, Optional, Union
from fastapi import APIRouter, Depends, status, Query, UploadFile, Form
from projects.schemas import ProjectInDB, ProjectCreate
from projects.dependencies import get_project_service
from pagination import PaginatedResponse, PaginationParams
from projects.services import ProjectService
from utils import FileService
from projects.openapi import PROJECT_CREATE_SCHEMA

router = APIRouter(prefix='/projects')

PROJECT_TAG = 'Projects'


@router.get(
    '/',
    tags=[PROJECT_TAG],
    response_model=PaginatedResponse[ProjectInDB],
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
):
    projects_in_db, total, total_pages = await service.get_all(
        search=search,
        ordering=ordering,
        offset=pagination_params.offset,
        limit=pagination_params.per_page
    )
    return PaginatedResponse(
        items=projects_in_db,
        per_page=pagination_params.per_page,
        page=pagination_params.page,
        total=total,
        total_pages=total_pages
    )


@router.post(
    '/',
    tags=[PROJECT_TAG],
    response_model=ProjectInDB,
    responses=PROJECT_CREATE_SCHEMA,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
        project_data: Annotated[str, Form(..., description='JSON string of user data')],
        document: Union[UploadFile, str, None] = Depends(FileService.parse_optional_file),
        service: ProjectService = Depends(get_project_service),
):
    return await service.create(project_data, document)


@router.delete(
    '/{project_id}',
    tags=[PROJECT_TAG],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
        project_id: int,
        service: ProjectService = Depends(get_project_service),
):
    return await service.delete(project_id)
