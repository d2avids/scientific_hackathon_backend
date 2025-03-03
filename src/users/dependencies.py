from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from users.repositories import UserRepo, UserDocumentRepo, RegionRepo
from users.services import UserService, UserDocumentService, RegionService
from database import get_db_session


async def get_user_repo(db: AsyncSession = Depends(get_db_session)) -> UserRepo:
    return UserRepo(db)


async def get_user_service(user_repo: UserRepo = Depends(get_user_repo)) -> UserService:
    return UserService(user_repo)


async def get_user_documents_repo(db: AsyncSession = Depends(get_db_session)) -> UserDocumentRepo:
    return UserDocumentRepo(db)


async def get_user_documents_service(
        documents_repo: UserDocumentRepo = Depends(get_user_documents_repo)) -> UserDocumentService:
    return UserDocumentService(documents_repo)


async def get_regions_repo(db: AsyncSession = Depends(get_db_session)) -> RegionRepo:
    return RegionRepo(db)


async def get_regions_service(region_repo: RegionRepo = Depends(get_regions_repo)) -> RegionService:
    return RegionService(region_repo)
