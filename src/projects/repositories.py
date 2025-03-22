from typing import Literal, Tuple, Sequence, Optional

from exceptions import NotFoundError
from projects.models import Project, Step
from projects.schemas import ProjectCreate, ProjectUpdate
from sqlalchemy import select, func, asc, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload


class ProjectRepo:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, project_id: int, join_steps: bool = False) -> Optional[Project]:
        base_query = select(Project).where(Project.id == project_id)
        if join_steps:
            base_query = base_query.options(
                joinedload(Project.steps)
            )
        result = await self._db.execute(base_query)
        return result.unique().scalar_one_or_none()

    async def get_all(
            self,
            *,
            search: str = None,
            order_column: str = 'id',
            order_direction: Literal['ASC', 'DESC'] = 'ASC',
            offset: int = 0,
            limit: int = 10,
    ) -> Tuple[Sequence[Project], int]:
        base_query = select(Project)
        count_query = select(func.count(Project.id))

        filters = []
        if search:
            filters.append(
                Project.name.ilike(f'%{search}%')
            )

        base_query = base_query.where(*filters)

        count_query = count_query.where(*filters)
        count_result = await self._db.execute(count_query)
        total = count_result.scalar() or 0

        column = getattr(Project, order_column, None)
        if column is not None:
            if order_direction == 'ASC':
                base_query = base_query.order_by(asc(column))
            else:
                base_query = base_query.order_by(desc(column))

        base_query = base_query.offset(offset).limit(limit)

        result = await self._db.execute(base_query)
        projects_list = result.scalars().all()

        return projects_list, total

    async def create(self, project_create: ProjectCreate) -> Project:
        async with self._db.begin():
            project = Project(**project_create.model_dump())
            self._db.add(project)
            await self._db.flush()
            await self._db.refresh(project)
            steps_to_create: list[Step] = []
            for step_number in range(1, 16):
                steps_to_create.append(
                    Step(
                        project_id=project.id,
                        step_number=step_number,
                    )
                )
            self._db.add_all(steps_to_create)
            await self._db.flush()
        return project

    async def update(self, update_data: dict, project: Project):
        for key, val in update_data.items():
            if hasattr(project, key):
                setattr(project, key, val)
        await self._db.commit()
        await self._db.refresh(project)
        return project

    async def set_document_path(self, project: Project, document_path: str) -> None:
        project.document_path = document_path
        await self._db.commit()
        await self._db.refresh(project)

    async def delete(self, project_id: int) -> None:
        query = delete(Project).where(Project.id == project_id)  # type: ignore
        await self._db.execute(query)
        await self._db.commit()
