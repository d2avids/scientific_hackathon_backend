from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from teams.repositories import TeamMemberRepo, TeamRepo
from teams.services import TeamMemberService, TeamService


async def get_team_repo(db: AsyncSession = Depends(get_db_session)) -> TeamRepo:
    return TeamRepo(db)


async def get_team_service(repo: TeamRepo = Depends(get_team_repo)) -> TeamService:
    return TeamService(repo)


async def get_team_member_repo(db: AsyncSession = Depends(get_db_session)) -> TeamMemberRepo:
    return TeamMemberRepo(db)


async def get_team_member_service(repo: TeamMemberRepo = Depends(get_team_member_repo)) -> TeamMemberService:
    return TeamMemberService(repo)
