from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.repositories import ResetCodeRepository
from auth.services import ResetCodeService
from database import get_db_session


async def get_reset_code_repo(db: AsyncSession = Depends(get_db_session)) -> ResetCodeRepository:
    return ResetCodeRepository(db)


async def get_reset_code_service(repo: ResetCodeRepository = Depends(get_reset_code_repo)) -> ResetCodeService:
    return ResetCodeService(repo)
