from fastapi import Depends, HTTPException, status
from users.models import User
from auth.services import get_current_user
from users.services import UserDocumentService
from users.dependencies import get_user_documents_service


async def require_mentor(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_mentor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Mentor privileges required'
        )
    return current_user


async def ensure_owner_or_admin(user_id: int, current_user: User = Depends(get_current_user)) -> User:
    if current_user.id == user_id and not current_user.is_mentor:
        return current_user
    if current_user.is_mentor:
        if current_user.mentor.is_admin:
            return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail='Not allowed to access data for other users'
    )


async def ensure_owner(user_id: int, current_user: User = Depends(get_current_user)) -> User:
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You are not allowed to modify this object'
        )
    return current_user


async def ensure_document_ownership(
        document_id: int,
        current_user: User = Depends(get_current_user),
        doc_service: UserDocumentService = Depends(get_user_documents_service)
) -> User:
    document = await doc_service.get_by_id(document_id)
    if document.user_id != current_user.id and not current_user.is_mentor and not current_user.mentor.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not allowed to delete this document'
        )
    return current_user
