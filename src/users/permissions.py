from typing import Optional
from fastapi import Depends, HTTPException, status

from auth.services import get_current_user
from teams.dependencies import get_team_member_repo
from teams.models import TeamMember
from teams.repositories import TeamMemberRepo
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


async def _verify_team_membership(
    team_id: int,
    current_user: User,
    team_member_repo: TeamMemberRepo
) -> tuple[User, Optional[TeamMember]]:
    """
    Вспомогательная функция для проверки членства пользователя в команде.
    Возвращает кортеж из текущего пользователя и объекта членства в команде.
    """
    if current_user.is_mentor:
        return current_user, None

    team_member = await team_member_repo.get_by_user_id(current_user.id)
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='The user is not a member of any team.'
        )
    if team_member.team_id != team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not allowed to access this team'
        )
    return current_user, team_member


async def ensure_team_member_or_mentor(
        team_id: int,
        current_user: User = Depends(get_current_user),
        team_member_repo: TeamMemberRepo = Depends(get_team_member_repo)
) -> User:
    """
    Ensure that the current user is a member of the specified team or is a mentor.
    """
    user, _ = await _verify_team_membership(team_id, current_user, team_member_repo)
    return user


async def ensure_captain_or_mentor(
        team_id: int,
        current_user: User = Depends(get_current_user),
        team_member_repo: TeamMemberRepo = Depends(get_team_member_repo)
) -> User:
    user, team_member = await _verify_team_membership(team_id, current_user, team_member_repo)

    if not current_user.is_mentor and team_member and not team_member.role_name.lower().startswith('капитан'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only the captain can perform this action.'
        )
    return user
