import datetime
import json
import mimetypes
from math import ceil
from typing import Optional, Sequence

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic_core import ValidationError

from projects.constants import PROJECT_FILES_MIME_TYPES, ProjectStatus
from projects.models import Project, Step, StepAttempt, StepComment, StepFile
from projects.repositories import ProjectRepo, StepRepo
from projects.schemas import ProjectCreate, ProjectInDB, ProjectUpdate
from users.models import User
from utils import (FileService, FileUploadResult, clean_errors,
                   create_field_map_for_model, dict_to_text, parse_ordering)


class ProjectService:
    field_map: dict = create_field_map_for_model(ProjectInDB)

    def __init__(self, repo: ProjectRepo):
        self._repo = repo

    @staticmethod
    async def _upload_document(document: UploadFile, project_id: str) -> FileUploadResult:
        return await FileService.upload_file(
            document,
            path_segments=['projects', project_id],
            allowed_mime_types=[
                'application/pdf',
                'text/plain',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ],
            size_limit_megabytes=10
        )

    async def get_by_id(
            self,
            project_id: int,
    ) -> Project:
        project = await self._repo.get_by_id(project_id, join_steps=True, join_team=True)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Project with ID {project_id} not found',
            )
        return project

    async def get_all(
            self,
            *,
            search: Optional[str] = None,
            ordering: Optional[str] = 'id',
            offset: int = 10,
            limit: int = 10,
    ) -> tuple[Sequence[Project], int, int]:
        order_column, order_direction = parse_ordering(ordering, self.field_map)

        result, total = await self._repo.get_all(
            search=search,
            order_column=order_column,
            order_direction=order_direction,
            offset=offset,
            limit=limit,
            join_team=True
        )
        total_pages = ceil(total / limit) if total > 0 else 1

        return result, total, total_pages

    async def get_project_files(self, project_id: int) -> Sequence[StepFile]:
        return await self._repo.get_project_files(project_id)

    async def create(
            self,
            *,
            project_create: str,
            document: UploadFile
    ) -> Project:
        try:
            data_dict = json.loads(project_create)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid JSON in user_data field.'
            )

        try:
            create_model = ProjectCreate(**data_dict)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=clean_errors(e.errors())
            )
        except TypeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Data string must be a valid JSON.'
            )

        project = await self._repo.create(create_model, commit=False)
        file_result = None
        try:
            file_result = await self._upload_document(document, str(project.id))
            await self._repo.set_document_path(project, file_result.relative_path)
        except Exception as e:
            if file_result:
                full_path = await FileService.construct_full_path_from_relative_path(file_result.relative_path)
                await FileService.delete_file_from_fs(full_path)
            raise e

        return project

    async def update(
            self,
            *,
            project_id: int,
            update_data: str,
            document: Optional[UploadFile]
    ) -> Project:
        project = await self.get_by_id(project_id)
        if update_data:
            try:
                data_dict = json.loads(update_data)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Invalid JSON in user_data field.'
                )

            try:
                update_model = ProjectUpdate(**data_dict)
            except ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=clean_errors(e.errors())
                )
            except TypeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Data string must be a valid JSON.'
                )

            update_dict = update_model.model_dump(exclude_unset=True)
        else:
            update_dict = {}

        if document:
            file_result = None
            try:
                file_result = await self._upload_document(document, str(project.id))
                update_dict['document_path'] = file_result.relative_path
                project = await self._repo.update(update_dict, project)
            except Exception as e:
                if file_result:
                    full_path = await FileService.construct_full_path_from_relative_path(file_result.relative_path)
                    await FileService.delete_file_from_fs(full_path)
                raise e
        else:
            project = await self._repo.update(update_dict, project)

        return project

    async def delete(self, project_id: int) -> None:
        project = await self._repo.get_by_id(project_id, join_steps=False)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Project with ID {project_id} not found',
            )

        await self._repo.delete(project_id)
        await FileService.delete_all_files_in_directory(['projects', str(project_id)])

    async def download_file(self, project_id: int, document_name: str):
        project = await self._repo.get_by_id(project_id, join_steps=False)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Project with ID {project_id} not found',
            )
        document_path = await FileService.get_doc_path(project_id, document_name, is_project=True)
        if not document_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'File {document_name} not found in project {project_id}'
            )
        media_type, _ = mimetypes.guess_type(document_name)
        return FileResponse(
            path=document_path,
            media_type=media_type or 'application/octet-stream',
            filename=document_name
        )

    async def download_all_files(self, project_id: int, background_tasks: BackgroundTasks) -> FileResponse:
        project = await self._repo.get_by_id(project_id, join_steps=True, join_team=True, join_comments=True)
        step_text = ''
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Project with ID {project_id} not found',
            )
        project_name = project.name
        if project.team:
            team_name = project.team.name
        else:
            team_name = 'Unknown team'

        for step in project.steps:
            step_text += dict_to_text(data={
                'Текст шага': step.text,
                'Очки': step.score,
                'Время': step.timer_minutes,
                'Статус': step.status,
                'Комментарии': [{
                    'Дата': datetime.datetime.strftime(comment.created_at, '%d.%m.%Y %H:%M:%S'),
                    'Пользователь': f'{comment.user.last_name} {comment.user.first_name}',
                    'Текст': comment.text,
                    'Файлы к комментарию': [f'{file.name}' for file in comment.files]
                } for comment in step.comments]},
                pretext=f'Шаг {step.step_number}:\n'
            ) + '\n'
        project_credits = f'Команда {team_name}. Проект {project_name}'
        project_description = f'{project_credits}\n{project.description}\n\n{step_text}'
        folder_path = FileService.get_media_folder_path(project_id=project_id, is_project=True)
        if not folder_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Project folder with ID {project_id} not found',
            )

        zip_path = await FileService.create_zip_from_directory(folder_path, project_description)
        background_tasks.add_task(FileService.delete_file_from_fs, zip_path)
        return FileResponse(
            path=zip_path,
            media_type='application/zip',
            filename=f'{project_credits}.zip'
        )


class StepService:
    def __init__(self, repo: StepRepo):
        self._repo = repo

    @staticmethod
    def _is_step_time_exceeded(step_attempt: StepAttempt) -> bool:
        """Check if the step time has exceeded."""
        return datetime.datetime.now(tz=datetime.timezone.utc) > step_attempt.end_time_at

    @staticmethod
    async def _upload_files(
            files: list[UploadFile],
            project_id: int,
            step_num: int,
            file_limit: int = 10,
            size_limit_mb: int = 100,
            comments: bool = False
    ) -> list:
        """Upload files with validation."""
        if len(files) > file_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Too many files to send. Maximum is {file_limit}'
            )

        files_to_create = []
        path_segments = ['projects', str(project_id), 'steps', str(step_num)]

        if comments:
            path_segments.append('comments')

        try:
            for file in files:
                result = await FileService.upload_file(
                    file=file,
                    path_segments=path_segments,
                    allowed_mime_types=PROJECT_FILES_MIME_TYPES,
                    size_limit_megabytes=size_limit_mb
                )
                files_to_create.append(result)
            return files_to_create
        except Exception as e:
            for file_to_create in files_to_create:
                await FileService.delete_file_from_fs(file_to_create.full_path)
            raise e

    @staticmethod
    async def _remove_step_files_from_fs(files: list[StepFile]) -> None:
        for file in files:
            full_path = await FileService.construct_full_path_from_relative_path(file.file_path)
            await FileService.delete_file_from_fs(full_path)

    async def _validate_previous_step_completed(self, project_id: int, step_num: int) -> None:
        """Validate that the previous step is completed."""
        if step_num <= 1:
            return

        previous_step = await self._repo.get_step(project_id=project_id, step_num=step_num - 1)
        if not previous_step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Previous step not found'
            )

        if previous_step.status != ProjectStatus.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Cannot start the new step until the previous step is finished'
            )

    async def get_step_or_404(
            self,
            *,
            project_id: int,
            step_num: int,
            join_files: bool = False,
            join_attempts: bool = False,
            join_comments: bool = False,
            join_project: bool = False,
            user: Optional[User] = None,
    ) -> Step:
        """Get a step or raise a 404 exception if not found.

        If user is passed, checks membership of a team this step is assigned by a project
        """
        join_team_members = True if user else False
        step = await self._repo.get_step(
            project_id=project_id,
            step_num=step_num,
            join_files=join_files,
            join_attempts=join_attempts,
            join_comments=join_comments,
            join_project=join_project,
            join_team_members=join_team_members
        )
        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Step not found'
            )
        if user and not user.is_mentor:
            if not step.project.team:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='You are not authorized to access this step'
                )

            team_member_participant_ids = {member.participant_id for member in step.project.team.team_members}
            if not user.participant or user.participant.id not in team_member_participant_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='You are not authorized to access this step'
                )
        return step

    async def start_step(
            self, *,
            project_id: int,
            step_num: int,
            user_team_id: int,
    ) -> Step:
        """Start a step for a project."""
        await self._validate_previous_step_completed(project_id, step_num)

        step = await self.get_step_or_404(project_id=project_id, step_num=step_num, join_project=True)
        if not step.project.team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Team for this project is not found'
            )
        if user_team_id != step.project.team.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='You are not authorized to access this step'
            )
        if step.status != ProjectStatus.NOT_STARTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Step is already started'
            )

        utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        end_time = utc_now + datetime.timedelta(minutes=step.timer_minutes)

        await self._repo.create_step_attempt(
            project_id=project_id,
            step_num=step_num,
            started_at=utc_now,
            end_time_at=end_time,
            step=step,
            commit=False
        )

        await self._repo.set_step_status(
            project_id=project_id,
            step_num=step_num,
            status=ProjectStatus.IN_PROGRESS,
            commit=True
        )

        return await self.get_step_or_404(
            project_id=project_id,
            step_num=step_num,
            join_files=True,
            join_attempts=True,
            join_comments=True
        )

    async def set_step_timer(self, *, project_id: int, step_num: int, timer: int) -> Step:
        """Set or update the timer for a step."""
        step = await self.get_step_or_404(
            project_id=project_id,
            step_num=step_num,
            join_comments=True,
            join_files=True,
            join_attempts=True
        )

        await self._repo.update_step(
            step=step,
            data={'timer_minutes': timer},
            commit=not step.status == ProjectStatus.IN_PROGRESS
        )

        if step.status == ProjectStatus.IN_PROGRESS:
            open_attempt = await self._repo.get_open_attempt(step_id=step.id, for_update=True)
            if not open_attempt:
                return step

            await self._repo.update_step_attempt_end_time_at(
                step_attempt=open_attempt,
                new_timer_minutes=timer,
                commit=True
            )

        return step

    async def submit_step(
            self,
            *,
            project_id: int,
            step_num: int,
            text: str,
            add_files: list[UploadFile],
            remove_file_ids: list[int],
            user_team_id: int
    ) -> Step:
        """Submit a step with text and files."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        step = await self.get_step_or_404(
            project_id=project_id,
            step_num=step_num,
            join_comments=True,
            join_attempts=True,
            join_project=True,
            join_files=True
        )

        if user_team_id != step.project.team.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='You are not authorized to access this step'
            )

        if step.status != ProjectStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Cannot submit step. First, start the step'
            )

        open_attempt = await self._repo.get_open_attempt(step_id=step.id)
        if not open_attempt:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='No active attempt to submit')

        file_models_to_remove: list[StepFile] = []
        if remove_file_ids:
            existing_by_id = {f.id: f for f in step.files}
            invalid_ids = [fid for fid in remove_file_ids if fid not in existing_by_id]
            if invalid_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Some files do not belong to this step: {invalid_ids}"
                )
            file_models_to_remove = [existing_by_id[fid] for fid in remove_file_ids]

        try:
            time_exceeded = self._is_step_time_exceeded(open_attempt)
            new_status = ProjectStatus.TIME_EXCEEDED if time_exceeded else ProjectStatus.SUBMITTED

            open_attempt.submitted_at = now

            await self._repo.update_step(
                step=step,
                data={'text': text, 'status': new_status},
                commit=False
            )

            if file_models_to_remove:
                await self._repo.delete_step_files_by_ids(step=step, file_ids=remove_file_ids, commit=False)
                await self._remove_step_files_from_fs(file_models_to_remove)

            files_to_create = await self._upload_files(add_files, project_id, step_num)
            if files_to_create:
                await self._repo.create_step_files(step=step, files=files_to_create, commit=False)

            await self._repo.set_new_submission(
                step=step,
                new_submission=True,
                commit=True
            )
        except Exception as e:
            if files_to_create:
                for file_result in files_to_create:
                    await FileService.delete_file_from_fs(file_result.full_path)
            raise e

        return step

    async def accept_step(self, *, project_id: int, step_num: int, score: int) -> Step:
        """Accept a submitted step with a score."""
        step = await self.get_step_or_404(
            project_id=project_id,
            step_num=step_num,
            join_files=True,
            join_attempts=True,
            join_comments=True,
            join_project=True
        )

        if step.status not in (ProjectStatus.SUBMITTED, ProjectStatus.TIME_EXCEEDED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Step has not been submitted'
            )

        await self._repo.update_step(
            step=step,
            data={
                'score': score,
                'status': ProjectStatus.ACCEPTED
            },
            commit=False
        )

        await self._repo.set_new_submission(
            step=step,
            new_submission=False,
            commit=True
        )

        return step

    async def reject_step(
            self,
            *,
            project_id: int,
            step_num: int,
            timer: Optional[int] = None
    ) -> Step:
        """Reject a submitted step."""
        step = await self.get_step_or_404(
            project_id=project_id,
            step_num=step_num,
            join_files=True,
            join_attempts=True,
            join_comments=True,
            join_project=True
        )

        if step.status not in (ProjectStatus.SUBMITTED, ProjectStatus.TIME_EXCEEDED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Step has not been submitted'
            )

        if not timer and step.status == ProjectStatus.SUBMITTED:
            last_submitted_attempt = await self._repo.get_last_submitted_attempt(
                step_id=step.id,
                for_update=False
            )
            if not last_submitted_attempt or not last_submitted_attempt.submitted_at:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No submitted attempt found to infer timer. Provide a new timer value."
                )

            delta = last_submitted_attempt.end_time_at - last_submitted_attempt.submitted_at
            minutes_left = max(1, round(delta.total_seconds() / 60.0))
            data = {'timer_minutes': minutes_left}
        else:
            data = {'timer_minutes': timer}

        data['status'] = ProjectStatus.NOT_STARTED

        await self._repo.update_step(
            step=step,
            data=data,
            commit=False
        )

        await self._repo.set_new_submission(
            step=step,
            new_submission=False,
            commit=True
        )

        return step

    async def get_comments(
            self,
            *,
            project_id: int,
            step_num: int,
            user: User
    ) -> Sequence[StepComment]:
        """Get all comments for a step."""
        step = await self.get_step_or_404(
            project_id=project_id,
            step_num=step_num,
            user=user
        )
        return await self._repo.get_comments(step=step, join_files=True)

    async def create_comment(
            self,
            *,
            project_id: int,
            step_num: int,
            text: str,
            files: list[UploadFile],
            user: User
    ) -> StepComment:
        """Create a comment on a step."""
        step = await self.get_step_or_404(project_id=project_id, step_num=step_num, user=user)
        if step.status == ProjectStatus.NOT_STARTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Step has not been started'
            )
        files_to_create = []
        if files:
            files_to_create = await self._upload_files(
                files,
                project_id,
                step_num,
                file_limit=5,
                comments=True
            )
        try:
            comment = await self._repo.create_comment(
                step=step,
                text=text,
                user=user,
                join_files=True,
                commit=not bool(files)  # commit if there are no files
            )

            if files:
                await self._repo.create_comment_files(
                    comment=comment,
                    files=files_to_create,
                    commit=True
                )
        except Exception as e:
            if files_to_create:
                for file_result in files_to_create:
                    await FileService.delete_file_from_fs(file_result.full_path)
            raise e

        return comment

    async def delete_comment(
            self,
            *,
            project_id: int,
            step_num: int,
            comment_id: int,
            user: User
    ) -> None:
        """Delete a comment if it belongs to the user or user is a mentor."""
        await self.get_step_or_404(project_id=project_id, step_num=step_num)

        comment = await self._repo.get_comment(comment_id=comment_id, join_files=True)
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Comment not found'
            )

        if comment.user_id != user.id and not user.is_mentor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='You can delete only your comments'
            )

        for file in comment.files:
            full_path = await FileService.construct_full_path_from_relative_path(file.file_path)
            await FileService.delete_file_from_fs(full_path)

        await self._repo.delete_comment(comment_id=comment_id)

    async def download_step_files(
        self,
        project_id: int,
        step_num: int,
        background_tasks: BackgroundTasks
    ) -> FileResponse:
        """
        Метод для скачивания всех файлов шага проекта в zip-архиве,
        включая текст шага и комментарии к нему.
        :param project_id: ID проекта
        :param step_num: Номер шага
        :param background_tasks: Фоновые задачи для удаления временных файлов
        :return: FileResponse с zip-архивом

        Метод собирает текст шага, комментарии к нему и файлы,
        создает zip-архив и возвращает его в ответе. Если папка с файлами шага не существует,
        то создается текстовый файл с информацией о шаге и комментариях. Далее путь текстового файла
        используется для создания zip-архива, который возвращается в ответе.
        """

        step = await self.get_step_or_404(project_id=project_id, step_num=step_num, join_comments=True)
        folder_path = FileService.get_media_folder_path(project_id=project_id, step_id=step_num, is_step=True)

        step_data = {
            'Текст шага': step.text,
            'Очки': step.score,
            'Время': step.timer_minutes,
            'Статус': step.status,
            'Комментарии': [{
                'Дата': datetime.datetime.strftime(comment.created_at, '%d.%m.%Y %H:%M:%S'),
                'Пользователь': f'{comment.user.last_name} {comment.user.first_name}',
                'Текст': comment.text,
                'Файлы к комментарию: ': [f'{file.name}' for file in comment.files]
            } for comment in step.comments]
        }
        file_text = dict_to_text(data=step_data, pretext=f'Шаг {step_num}:\r\n')

        if not folder_path.exists():
            text_file_path = await FileService.create_response_file(
                text=file_text,
                file_name='temp_file.txt'
            )
            folder_path = FileService.get_doc_path_from_full_path(text_file_path)
            background_tasks.add_task(FileService.delete_file_from_fs, text_file_path)

        zip_path = await FileService.create_zip_from_directory(
            folder_path=folder_path,
            text=file_text,
            file_name=f'Текст и комментарии шага {step_num}.txt'
        )
        background_tasks.add_task(FileService.delete_file_from_fs, zip_path)
        return FileResponse(
            path=zip_path,
            media_type='application/zip',
            filename=f'step_{step_num}_files.zip'
        )
