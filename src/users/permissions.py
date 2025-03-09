from auth.services import get_current_user
from fastapi import Depends, HTTPException, status
from users.dependencies import get_user_documents_repo
from users.models import User, UserDocument
from users.services import UserDocumentRepo


async def require_mentor(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_mentor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Mentor privileges required.'
        )
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.is_mentor:
        if current_user.mentor.is_admin:
            return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail='Admin privileges required.'
    )


async def ensure_owner_or_admin(user_id: int, current_user: User = Depends(get_current_user)) -> User:
    if current_user.id == user_id and not current_user.is_mentor:
        return current_user
    if current_user.is_mentor:
        if current_user.mentor.is_admin:
            return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail='Not allowed to access data for other users.'
    )


async def ensure_owner(user_id: int, current_user: User = Depends(get_current_user)) -> User:
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You are not allowed to modify this object.'
        )
    return current_user


async def ensure_document_ownership(
        document_id: int,
        current_user: User = Depends(get_current_user),
        doc_repo: UserDocumentRepo = Depends(get_user_documents_repo)
) -> UserDocument:
    document = await doc_repo.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Document not found'
        )
    if document.user_id != current_user.id and not current_user.is_mentor and not current_user.mentor.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not allowed to delete this document.'
        )
    return document
