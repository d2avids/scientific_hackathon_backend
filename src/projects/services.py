import json
from math import ceil
from typing import Tuple

from fastapi import UploadFile, HTTPException, status
from projects.repositories import ProjectRepo
from projects.schemas import ProjectInDB, ProjectCreate, ProjectWithStepsInDB
from pydantic_core import ValidationError
from utils import create_field_map_for_model, parse_ordering, FileService, clean_errors


class ProjectService:
    field_map: dict = create_field_map_for_model(ProjectInDB)

    def __init__(self, repo: ProjectRepo):
        self._repo = repo

    async def get_by_id(
            self,
            project_id: int,
    ) -> ProjectWithStepsInDB:
        project = await self._repo.get_by_id(project_id, join_steps=True)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Project with ID {project_id} not found',
            )
        return ProjectWithStepsInDB.model_validate(project)

    async def get_all(
            self,
            *,
            search: str = None,
            ordering: str = 'id',
            offset: int = 10,
            limit: int = 10,
    ) -> Tuple[list[ProjectInDB], int, int]:
        order_column, order_direction = parse_ordering(ordering, self.field_map)

        result, total = await self._repo.get_all(
            search=search,
            order_column=order_column,
            order_direction=order_direction,
            offset=offset,
            limit=limit,
        )

        projects_in_db = [ProjectInDB.model_validate(p) for p in result]

        total_pages = ceil(total / limit) if total > 0 else 1

        return projects_in_db, total, total_pages

    async def create(self, project_create: str, document: UploadFile) -> ProjectInDB:
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

        project = await self._repo.create(create_model)

        result = await FileService.upload_file(
            document,
            path_segments=['projects', str(project.id)],
            allowed_mime_types=[
                'application/pdf',
                'text/plain',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ],
            size_limit_megabytes=10
        )
        await self._repo.set_document_path(project, result.relative_path)

        return ProjectInDB.model_validate(project)

    async def delete(self, project_id: int) -> None:
        project = await self._repo.get_by_id(project_id, join_steps=False)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Project with ID {project_id} not found',
            )

        await self._repo.delete(project_id)
        document_path = await FileService.construct_full_path_from_relative_path(project.document_path)
        await FileService.delete_file_from_fs(document_path)
