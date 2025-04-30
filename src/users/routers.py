from typing import Annotated, Optional, Union

from fastapi import status, APIRouter, Query, Depends, Form, UploadFile, File, BackgroundTasks

from auth.services import get_current_user
from openapi import AUTHENTICATION_RESPONSES, NOT_FOUND_RESPONSE
from pagination import PaginatedResponse, PaginationParams
from users.dependencies import get_regions_service, get_user_service, get_user_documents_service
from users.models import User, UserDocument
from users.openapi import (
    USER_CREATE_RESPONSES,
    USER_UPDATE_SCHEMA,
    USER_UPDATE_RESPONSES,
    USER_DOCUMENTS_CREATE_RESPONSES,
    USER_GET_RESPONSES,
    USER_VERIFY_RESPONSES,
)
from permissions import require_mentor, ensure_owner_or_admin, ensure_document_ownership, require_admin
from users.schemas import UserInDB, RegionInDB, UserCreate, UserDocumentInDB
from users.services import RegionService, UserService, UserDocumentService
from utils import FileService

router = APIRouter()

REGIONS_PREFIX = 'Regions'
USERS_PREFIX = 'Users'
USER_DOCUMENTS_PREFIX = 'User Documents'


@router.get(
    '/regions',
    tags=[REGIONS_PREFIX],
    response_model=list[RegionInDB]
)
async def get_regions(
        search: Annotated[Optional[str], Query(
            title='Partial Name Search',
            description='Case-insensitive search on region name.'
        )] = None,
        name: Annotated[Optional[str], Query(
            title='Exact Name Filter',
            description='Return regions matching the exact name.'
        )] = None,
        code: Annotated[Optional[int], Query(
            title='Exact Code Filter',
            description='Return regions matching the exact region code.'
        )] = None,
        service: RegionService = Depends(get_regions_service)
):
    """## Regions list. No permissions required."""
    return await service.get_all(search, name, code)


@router.get(
    '/users/me',
    tags=[f'{USERS_PREFIX} Read'],
    responses={**AUTHENTICATION_RESPONSES, },
    response_model=UserInDB
)
async def get_user(
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(get_current_user),
):
    """## Get current user. Any authenticated user is allowed."""
    return await service.get_by_id(current_user.id)


@router.get(
    '/users/{user_id}',
    tags=[f'{USERS_PREFIX} Read'],
    responses={
        **AUTHENTICATION_RESPONSES,
        **USER_GET_RESPONSES,
    },
    response_model=UserInDB
)
async def get_user(
        user_id: int,
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(get_current_user),
):
    """## Get user instance by user_id. Any authenticated user is allowed."""
    return await service.get_by_id(user_id)


@router.get(
    '/users',
    tags=[f'{USERS_PREFIX} Read'],
    responses={**AUTHENTICATION_RESPONSES, },
    response_model=PaginatedResponse[UserInDB]
)
async def get_users(
        pagination_params: PaginationParams = Depends(),
        search: Annotated[Optional[str], Query(
            title='Partial Search',
            description='Search by first name, last name, or email.'
        )] = None,
        is_mentor: Annotated[Optional[bool], Query(
            title='User Type Filter',
            description='True for mentors, false for participants.'
        )] = None,
        ordering: Annotated[Optional[str], Query(
            title='Ordering',
            description='Sort field; prefix with "-" for descending order.'
        )] = None,
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(require_mentor),
):
    """## Get all users. Only mentors are allowed."""
    users, total, total_pages = await service.get_all(
        search=search,
        is_mentor=is_mentor,
        ordering=ordering,
        offset=pagination_params.offset,
        limit=pagination_params.per_page,
    )

    return PaginatedResponse[UserInDB](
        items=users,
        total=total,
        page=pagination_params.page,
        per_page=pagination_params.per_page,
        total_pages=total_pages
    )


@router.post(
    '/users',
    tags=[f'{USERS_PREFIX} Registration'],
    responses=USER_CREATE_RESPONSES,
    status_code=status.HTTP_201_CREATED,
    response_model=UserInDB
)
async def create_user(
        user_data: UserCreate,
        service: UserService = Depends(get_user_service)
):
    """## Registration. No permissions required."""
    return await service.create(user_data)


@router.patch(
    '/users/{user_id}',
    tags=[f'{USERS_PREFIX} Update'],
    response_model=UserInDB,
    responses={
        **AUTHENTICATION_RESPONSES,
        **USER_UPDATE_RESPONSES
    },
    openapi_extra=USER_UPDATE_SCHEMA
)
async def update_user(
        user_id: int,
        data: Annotated[str, Form(description="JSON string of user data")] = None,
        photo: Union[UploadFile, str, None] = Depends(FileService.create_parse_optional_file('photo')),
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(ensure_owner_or_admin),
):
    """
    ## Partial update via multipart/form-data format. Params:
      - data (JSON string with camelCase fields)
      - photo (optionally file or empty string)

    Note:
      - If photo sent as an empty value `''`, existing photo will be deleted from fs and set to null
      - If photo is not sent at all, existing photo won't be changed or set to null
    """
    updated_user = await service.update(user_id, data, current_user, photo)
    return updated_user


@router.post(
    '/users/{user_id}/verify',
    tags=[f'{USERS_PREFIX} Update'],
    responses={
        **AUTHENTICATION_RESPONSES,
        **USER_VERIFY_RESPONSES,
    },
    status_code=status.HTTP_204_NO_CONTENT
)
async def verify_user(
        user_id: int,
        background_tasks: BackgroundTasks,
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(require_admin),
):
    """## Verify user's registration. Only admins are allowed."""
    await service.verify(user_id, background_tasks)


@router.delete(
    '/users/{user_id}/verify',
    tags=[f'{USERS_PREFIX} Update'],
    responses={
        **AUTHENTICATION_RESPONSES,
        **USER_VERIFY_RESPONSES,
    },
    status_code=status.HTTP_204_NO_CONTENT
)
async def verify_user(
        user_id: int,
        background_tasks: BackgroundTasks,
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(require_admin),
):
    """## Decline user's registration. Deletes user's instance. Only admins are allowed."""
    await service.decline_registration(user_id, background_tasks)


@router.delete(
    '/users/{user_id}',
    tags=[f'{USERS_PREFIX} Delete'],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE,
    },
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(
        user_id: int,
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(require_mentor),
):
    """## Delete user. Mentors rights required"""
    await service.delete(user_id)


@router.get(
    '/users/{user_id}/documents',
    tags=[USER_DOCUMENTS_PREFIX],
    responses={**AUTHENTICATION_RESPONSES, },
    response_model=list[UserDocumentInDB]
)
async def get_user_documents(
        user_id: int,
        service: UserDocumentService = Depends(get_user_documents_service),
        current_user: User = Depends(get_current_user),
):
    """## Get user's documents. Any authenticated user is allowed."""
    return await service.get_user_documents(user_id)


@router.post(
    '/users/documents',
    tags=[USER_DOCUMENTS_PREFIX],
    responses={
        **AUTHENTICATION_RESPONSES,
        **USER_DOCUMENTS_CREATE_RESPONSES,
    },
    status_code=status.HTTP_201_CREATED,
    response_model=UserDocumentInDB
)
async def create_user_document(
        uploaded_file: Annotated[UploadFile, File(
            ...,
            title='Document File',
            description='File to upload.'
        )],
        service: UserDocumentService = Depends(get_user_documents_service),
        current_user: User = Depends(get_current_user),
):
    """## Create document. Any authenticated user is allowed.

    Only 5 files per user. Allowed mime types up to 10 megabytes:
      - `application/pdf`
      - `application/msword`
      - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
      - `text/plain`
    """
    return await service.create(current_user.id, uploaded_file)


@router.delete(
    '/users/documents/{document_id}',
    tags=[USER_DOCUMENTS_PREFIX],
    responses={
        **AUTHENTICATION_RESPONSES,
        **NOT_FOUND_RESPONSE
    },
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_document(
        document_id: int,
        service: UserDocumentService = Depends(get_user_documents_service),
        document: UserDocument = Depends(ensure_document_ownership)
):
    """## Delete document by id. Only admin or document's owner are allowed."""
    await service.delete(document_id, document)
