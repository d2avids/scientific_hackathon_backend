from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from projects.repositories import ProjectRepo, StepRepo
from projects.services import ProjectService, StepService


async def get_project_repo(db_session: AsyncSession = Depends(get_db_session)) -> ProjectRepo:
    return ProjectRepo(db_session)


async def get_project_service(project_repo: ProjectRepo = Depends(get_project_repo)) -> ProjectService:
    return ProjectService(project_repo)


async def get_step_repo(db_session: AsyncSession = Depends(get_db_session)) -> StepRepo:
    return StepRepo(db_session)


async def get_step_service(step_repo: StepRepo = Depends(get_step_repo)) -> StepService:
    return StepService(step_repo)
