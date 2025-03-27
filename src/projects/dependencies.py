from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from projects.repositories import ProjectRepo
from projects.services import ProjectService


async def get_project_repo(db_session: AsyncSession = Depends(get_db_session)) -> ProjectRepo:
    return ProjectRepo(db_session)


async def get_project_service(project_repo: ProjectRepo = Depends(get_project_repo)) -> ProjectService:
    return ProjectService(project_repo)
