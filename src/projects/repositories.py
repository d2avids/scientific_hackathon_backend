from datetime import datetime, timedelta
from typing import Literal, Sequence, Optional

from sqlalchemy import select, func, asc, desc, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from exceptions import NotFoundError
from projects.constants import ProjectStatus
from projects.models import Project, Step, StepComment, StepAttempt, StepFile, StepCommentFile
from projects.schemas import ProjectCreate
from teams.models import Team
from users.models import User
from utils import FileUploadResult


class ProjectRepo:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, project_id: int, join_steps: bool = False) -> Optional[Project]:
        base_query = select(Project).where(Project.id == project_id)  # type: ignore
        if join_steps:
            base_query = base_query.options(
                # joinedload is fine since there are only 15 steps
                joinedload(Project.steps)
            )
        result = await self._db.execute(base_query)
        return result.unique().scalar_one_or_none()

    async def get_all(
            self,
            *,
            search: Optional[str] = None,
            order_column: Optional[str] = 'id',
            order_direction: Literal['ASC', 'DESC'] = 'ASC',
            offset: int = 0,
            limit: int = 10,
    ) -> tuple[Sequence[Project], int]:
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

    async def create(self, project_create: ProjectCreate, commit: bool = True) -> Project:
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

        if commit:
            await self._db.commit()

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


class StepRepo:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_step(
            self,
            *,
            project_id: int,
            step_num: int,
            join_attempts: bool = False,
            join_files: bool = False,
            join_comments: bool = False,
            join_project: bool = False,
            join_team_members: bool = False
    ) -> Optional[Step]:
        query = (
            select(Step).where(
                Step.project_id == project_id, Step.step_number == step_num  # type: ignore
            )
        )

        if join_attempts:
            # joinedload is justified here since generally there
            # won't be too many attempts, therefore it's more efficient
            query = query.options(joinedload(Step.attempts))
        if join_files:
            # same for files (no more than 10)
            query = query.options(joinedload(Step.files))
        if join_comments:
            query = query.options(
                joinedload(Step.comments),
                joinedload(Step.comments).joinedload(StepComment.files),
                joinedload(Step.comments).joinedload(StepComment.user),
            )
        if join_project and not join_team_members:
            query = query.options(
                joinedload(Step.project).joinedload(Project.team)
            )
        if join_team_members:
            query = query.options(
                joinedload(Step.project).joinedload(Project.team).selectinload(Team.team_members),
            )

        result = await self._db.execute(query)
        return result.unique().scalar_one_or_none()

    async def set_step_status(
            self,
            *,
            project_id: int,
            step_num: int,
            status: ProjectStatus,
            commit: bool = True
    ) -> None:
        await self._db.execute(update(Step).where(
            Step.project_id == project_id,  # type: ignore
            Step.step_number == step_num  # type: ignore
        ).values(status=status))

        await self._db.flush()

        if commit:
            await self._db.commit()

    async def create_step_attempt(
            self,
            *,
            project_id: int,
            step_num: int,
            started_at: datetime,
            end_time_at: datetime,
            step: Optional[Step] = None,
            commit: bool = True,
    ) -> StepAttempt:
        if step is None:
            step = await self.get_step(project_id=project_id, step_num=step_num)

        if not step:
            raise NotFoundError

        step_attempt = StepAttempt(
            step_id=step.id,
            started_at=started_at,
            end_time_at=end_time_at
        )
        self._db.add(step_attempt)
        await self._db.flush()

        if commit:
            await self._db.commit()

        return step_attempt

    async def update_step_attempt_end_time_at(
            self,
            *,
            step_attempt: StepAttempt,
            new_timer_minutes: int,
            commit: bool = True
    ) -> None:
        step_attempt.end_time_at = step_attempt.started_at + timedelta(minutes=new_timer_minutes)
        await self._db.flush()

        if commit:
            await self._db.commit()

        await self._db.refresh(step_attempt.step, attribute_names=('attempts',))

    async def update_step(
            self,
            *,
            step: Step,
            data: dict,
            commit: bool = True
    ) -> Step:
        for key, val in data.items():
            if hasattr(step, key):
                setattr(step, key, val)
        await self._db.flush()

        if commit:
            await self._db.commit()

        await self._db.refresh(step)
        return step

    async def set_new_submission(
            self,
            *,
            step: Step,
            new_submission: bool,
            commit: bool = True,
    ) -> None:
        step.project.new_submission = new_submission
        await self._db.flush()
        if commit:
            await self._db.commit()

    async def clear_step_files(self, step: Step, commit: bool = False) -> None:
        await self._db.execute(delete(StepFile).where(StepFile.step_id == step.id))  # type: ignore
        await self._db.flush()
        await self._db.refresh(step, attribute_names=('files',))
        if commit:
            await self._db.commit()

    async def create_step_files(
            self,
            *,
            step: Step,
            files: list[FileUploadResult],
            commit: bool = True
    ) -> None:
        step_files = [
            StepFile(
                step=step,
                file_path=file.relative_path,
                name=file.name,
                mimetype=file.mime_type,
                size=file.size_bytes,
            ) for file in files
        ]
        self._db.add_all(step_files)
        await self._db.flush()
        await self._db.refresh(step, attribute_names=('files',))

        if commit:
            await self._db.commit()

    async def get_comment(
            self,
            *,
            comment_id: int,
            join_files: bool = False,
    ) -> Optional[StepComment]:
        query = select(StepComment).where(StepComment.id == comment_id)  # type: ignore
        if join_files:
            query = query.options(joinedload(StepComment.files))
        result = await self._db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_comments(
            self,
            *,
            step: Step,
            join_files: bool = False,
    ) -> Sequence[StepComment]:
        query = select(StepComment).where(StepComment.step == step).order_by('created_at')  # type: ignore
        query = query.options(joinedload(StepComment.user))
        if join_files:
            # files are limited, so joinedload is justified
            query = query.options(joinedload(StepComment.files))
        result = await self._db.execute(query)
        return result.unique().scalars().all()

    async def create_comment(
            self,
            *,
            step: Step,
            text: str,
            user: User,
            join_files: bool = False,
            commit: bool = True
    ) -> StepComment:
        comment = StepComment(step=step, user=user, text=text)
        self._db.add(comment)
        await self._db.flush()

        if commit:
            await self._db.commit()

        if join_files:
            query = select(StepComment).where(
                StepComment.id == comment.id  # type: ignore
            ).options(joinedload(StepComment.files))
            result = await self._db.execute(query)
            comment = result.unique().scalar_one()
        else:
            await self._db.refresh(comment)

        return comment

    async def create_comment_files(
            self,
            *,
            comment: StepComment,
            files: list[FileUploadResult],
            commit: bool = True
    ):
        comment_files = [
            StepCommentFile(
                comment=comment,
                file_path=file.relative_path,
                name=file.name,
                mimetype=file.mime_type,
                size=file.size_bytes
            ) for file in files
        ]
        self._db.add_all(comment_files)
        await self._db.flush()
        if commit:
            await self._db.commit()
        await self._db.refresh(comment, attribute_names=('files',))

    async def delete_comment(
            self,
            *,
            comment_id: int
    ) -> None:
        await self._db.execute(delete(StepComment).where(StepComment.id == comment_id))  # type: ignore
        await self._db.commit()
