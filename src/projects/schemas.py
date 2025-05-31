from datetime import datetime
from typing import Annotated, Optional
from urllib.parse import urljoin

from pydantic import Field, field_serializer, model_validator

from projects.constants import MODIFY_STEP_ACTIONS
from projects.models import Project
from schemas import ConfiguredModel, IDModel
from settings import settings
from users.schemas import ShortUserInDB


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
    new_submission: Annotated[
        bool,
        Field(
            ...,
            title='New submission status',
            description='Indicates whether there is an unchecked step submission for a mentor'
        )
    ]
    created_at: Annotated[
        datetime,
        Field(
            ...,
            title='Created at',
        )
    ]
    updated_at: Annotated[
        Optional[datetime],
        Field(
            title='Updated at',
        )
    ]

    @field_serializer('document_path')
    def _document_path_serializer(self, document_path: Optional[str]) -> Optional[str]:
        """Generates url path to the file."""
        if document_path is None:
            return None
        return urljoin(settings.SERVER_URL, document_path)


class ProjectRead(ProjectInDB):
    team_id: Annotated[
        Optional[int],
        Field(title='Team id'),
    ]

    @model_validator(mode='before')
    @classmethod
    def inject_team_id(cls, data):

        if isinstance(data, Project):
            return {
                **data.__dict__,
                'team_id': data.team.id if data.team else None,
            }
        return data


class ProjectWithStepsInDB(ProjectRead):
    steps: Annotated[
        list['StepInDB'],
        Field(
            ...,
            title='Steps of the project',
        )
    ]


class ProjectCreate(ProjectBase):
    ...


class ProjectUpdate(ConfiguredModel):
    name: Annotated[
        Optional[str],
        Field(
            title='Project name',
            max_length=50,
        )
    ]
    description: Annotated[
        Optional[str],
        Field(
            title='Project description',
            max_length=500,
        )
    ]

    @model_validator(mode='before')
    @classmethod
    def check_explicit_null_fields(cls, values):
        fields_cant_be_none_if_present = [
            'name',
            'description',
        ]
        for field_name in fields_cant_be_none_if_present:
            if field_name in values and not values[field_name]:
                raise ValueError(f'{field_name} cannot be null if explicitly passed')

        return values


class StepBase(ConfiguredModel):
    project_id: Annotated[int, Field(..., title='Project ID')]
    step_number: Annotated[int, Field(..., title='Step number')]
    text: Annotated[Optional[str], Field(None, title='Team\'s answer on this step')]
    score: Annotated[int, Field(..., title='Score')]
    timer_minutes: Annotated[int, Field(..., title='Timer minutes')]
    status: Annotated[str, Field(..., title='Status')]
    updated_at: Annotated[Optional[datetime], Field(None, title='Updated at')]


class StepInDB(StepBase, IDModel):
    """Step schema for list of steps."""


class StepAttemptInDB(ConfiguredModel):
    started_at: Annotated[datetime, Field(...)]
    end_time_at: Annotated[datetime, Field(...)]
    submitted_at: Annotated[Optional[datetime], Field(None)]


class FileInDB(ConfiguredModel):
    file_path: Annotated[str, Field(...)]
    name: Annotated[str, Field(title='File name', )]
    size: Annotated[float, Field(title='File size', description='File size represented in bytes', )]
    mimetype: Annotated[str, Field(title='File mimetype', )]

    @field_serializer('file_path')
    def _file_path_serializer(self, file_path: Optional[str]) -> Optional[str]:
        """Generates url path to the file."""
        if file_path is None:
            return None
        return urljoin(settings.SERVER_URL, file_path)


class StepCommentInDB(ConfiguredModel, IDModel):
    user: Annotated[ShortUserInDB, Field(...)]
    text: Annotated[str, Field(...)]
    created_at: Annotated[datetime, Field(...)]
    files: Annotated[list[FileInDB], Field(default_factory=list)]


class StepWithRelations(StepInDB):
    attempts: Annotated[list[StepAttemptInDB], Field(default_factory=list)]
    files: Annotated[list[FileInDB], Field(default_factory=list)]
    comments: Annotated[list[StepCommentInDB], Field(default_factory=list)]


class StepModify(ConfiguredModel):
    action: Annotated[MODIFY_STEP_ACTIONS, Field(None, title='Action')]
    timer: Annotated[Optional[int], Field(None, title='New timer value', gt=0, description='Timer value in minutes')]
    score: Annotated[Optional[int], Field(None, title='Score value', gt=0, lt=11)]

    @model_validator(mode='after')
    def validate_action(self):
        if self.action == 'set-timer' and self.timer is None:
            raise ValueError('timer should be provided when setting timer')
        if self.action == 'accept' and self.score is None:
            raise ValueError('score should be provided when accepting the attempt')
        return self
