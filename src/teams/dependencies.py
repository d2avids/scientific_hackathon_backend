from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from teams.repositories import TeamRepo
from teams.services import TeamService
from database import get_db_session


async def get_team_repo(db: AsyncSession = Depends(get_db_session)) -> TeamRepo:
    return TeamRepo(db)


async def get_team_service(repo: TeamRepo = Depends(get_team_repo)) -> TeamService:
    return TeamService(repo)
