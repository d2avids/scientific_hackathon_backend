from typing import Annotated, Optional
from urllib.parse import urljoin

from pydantic import Field, field_serializer
from schemas import ConfiguredModel, IDModel
from settings import settings


class ProjectBase(ConfiguredModel):
    name: Annotated[
        str,
        Field(
            ...,
            title='Project name',
            max_length=50,
        )
    ]
    description: Annotated[
        str,
        Field(
            ...,
            title='Project description',
            max_length=500,
        )
    ]


class ProjectInDB(ProjectBase, IDModel):
    document_path: Annotated[
        str,
        Field(
            ...,
            title='Document path',
        )
    ]
    score: Annotated[
        int,
        Field(
            ...,
            title='Sum of step scores for this project'
        )
    ]

    @field_serializer('document_path')
    def _document_path_serializer(self, document_path: Optional[str]) -> Optional[str]:
        """Generates url path to the file."""
        if document_path is None:
            return None
        return urljoin(settings.SERVER_URL, document_path)


class ProjectCreate(ProjectBase):
    ...


class StepInDB(ConfiguredModel, IDModel):
    project_id: Annotated[
        int,
        Field(
            ...,
            title='Project ID',
        )
    ]
    step_number: Annotated[
        int,
        Field(
            ...,
            title='Step number',
        )
    ]
    text: Annotated[
        str,
        Field(
            ...,
            title='Team\'s answer on this step',
        )
    ]
    score: Annotated[
        int,
        Field(
            ...,
            title='Score',
        )
    ]
    timer_minutes: Annotated[
        int,
        Field(
            ...,
            title='Timer minutes',
        )
    ]
    status: Annotated[
        str,
        Field(
            ...,
            title='Status',
        )
    ]
