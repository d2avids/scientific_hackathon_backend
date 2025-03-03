import json
from typing import Annotated, Optional

from pydantic_core import ValidationError

from fastapi import status, APIRouter, Query, Depends, Form, UploadFile, File, HTTPException
from users.constants import USER_UPDATE_SCHEMA

from users.dependencies import get_regions_service, get_user_service, get_user_documents_service
from users.permissions import require_mentor, ensure_owner_or_admin, ensure_document_ownership
from users.schemas import UserInDB, RegionInDB, UserCreate, UserDocumentInDB, UserUpdate
from users.services import RegionService, UserService, UserDocumentService

from auth.services import get_current_user
from users.models import User
from utils import parse_optional_file

router = APIRouter()

REGIONS_PREFIX = 'Regions'
USERS_PREFIX = 'Users'
USER_DOCUMENTS_PREFIX = 'User Documents'


@router.get('/regions', tags=[REGIONS_PREFIX], response_model=list[RegionInDB])
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
    """Regions list. No permissions required."""
    return await service.get_all(search, name, code)


@router.get('/users/me', tags=[f'{USERS_PREFIX} Read'], response_model=UserInDB)
async def get_user(
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(get_current_user),
):
    """Get current user. Any authenticated user is allowed."""
    return await service.get_by_id(current_user.id)


@router.get('/users/{user_id}', tags=[f'{USERS_PREFIX} Read'], response_model=UserInDB)
async def get_user(
        user_id: int,
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(get_current_user),
):
    """Get user instance by user_id. Any authenticated user is allowed."""
    return await service.get_by_id(user_id)


@router.get('/users', tags=[f'{USERS_PREFIX} Read'], response_model=list[UserInDB])
async def get_users(
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
    """Get all users. Only mentors are allowed."""
    return await service.get_all(search, is_mentor, ordering)


@router.post('/users', tags=[f'{USERS_PREFIX} Registration'], response_model=UserInDB)
async def create_user(
        user_data: UserCreate,
        service: UserService = Depends(get_user_service)
):
    """Registration. No permissions required."""
    return await service.create(user_data)


@router.patch(
    '/users/{user_id}',
    tags=[f'{USERS_PREFIX} Update'],
    response_model=UserInDB,
    openapi_extra=USER_UPDATE_SCHEMA
)
async def update_user(
        user_id: int,
        data: Annotated[str, Form(..., description="JSON string of user data")],
        photo: Optional[UploadFile] = Depends(parse_optional_file),
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(ensure_owner_or_admin),
):
    """
    Partial update via multipart/form-data format. Params:
      - data (JSON string with camelCase fields)
      - photo (optionally file or empty value/null)
    """
    try:
        data_dict = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in user_data field")

    try:
        update_model = UserUpdate(**data_dict)
    except ValidationError as e:
        errors = e.errors()
        for err in errors:
            if 'ctx' in err and 'error' in err['ctx']:
                err['ctx']['error'] = str(err['ctx']['error'])

        raise HTTPException(status_code=422, detail=errors)

    update_dict = update_model.model_dump(exclude_unset=True)
    updated_user = await service.update(user_id, update_dict, photo)
    return updated_user


@router.post('/users/{user_id}/verify', tags=[f'{USERS_PREFIX} Update'], status_code=status.HTTP_204_NO_CONTENT)
async def verify_user(
        user_id: int,
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(require_mentor),
):
    """Verify user's registration. Only mentors are allowed."""
    await service.verify(user_id)


@router.delete('/users/{user_id}/verify', tags=[f'{USERS_PREFIX} Update'], status_code=status.HTTP_204_NO_CONTENT)
async def verify_user(
        user_id: int,
        service: UserService = Depends(get_user_service),
        current_user: User = Depends(require_mentor),
):
    """Decline user's registration. Deletes user's instance. Only mentors are allowed."""
    await service.decline_registration(user_id)


@router.get('/users/{user_id}/documents', tags=[USER_DOCUMENTS_PREFIX], response_model=list[UserDocumentInDB])
async def get_user_documents(
        user_id: int,
        service: UserDocumentService = Depends(get_user_documents_service),
        current_user: User = Depends(get_current_user),
):
    """Get user's documents. Any authenticated user is allowed."""
    return await service.get_user_documents(user_id)


@router.post('/users/documents', tags=[USER_DOCUMENTS_PREFIX], response_model=UserDocumentInDB)
async def create_user_document(
        uploaded_file: Annotated[UploadFile, File(
            ...,
            title='Document File',
            description='File to upload.'
        )],
        service: UserDocumentService = Depends(get_user_documents_service),
        current_user: User = Depends(get_current_user),
):
    """Create document. Any authenticated user is allowed."""
    return await service.create(current_user.id, uploaded_file)


@router.delete('/documents/{document_id}', tags=[USER_DOCUMENTS_PREFIX], status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
        document_id: int,
        service: UserDocumentService = Depends(get_user_documents_service),
        current_user: User = Depends(ensure_document_ownership)
):
    """Delete document by id. Only admin or document's owner are allowed."""
    await service.delete(document_id)
