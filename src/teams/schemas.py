from typing import Annotated, List, Optional
from pydantic import Field, field_validator, model_validator
from schemas import ConfiguredModel, CreatedUpdatedAt
from users.schemas import ParticipantInDB


class TeamMemberBase(ConfiguredModel):
    """Schema for a team member to be returned."""
    id: Annotated[
        int,
        Field(
            title='Team Member ID',
            description='The ID of the team member.'
        )
    ]
    role_name: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Role Name',
            description='The role of the participant in the team.',
            max_length=250
        )
    ]

    @field_validator('role_name')
    @classmethod
    def validate_role_format(cls, v):
        if v and not v.replace(' ', '').isalpha():
            raise ValueError("Role name can only contain letters and spaces")
        return v


class TeamMemberCreate(TeamMemberBase):
    """Schema for creating a team member."""
    participant_id: Annotated[
        int,
        Field(
            ...,
            title='Participant ID',
            description='The ID of the participant who is a member of the team.'
        )
    ]


class TeamMemberInDB(CreatedUpdatedAt, TeamMemberBase):
    """Schema for a team member to be returned."""
    participant: Annotated[
        ParticipantInDB,
        Field(
            title='Participant',
            description='The participant who is a member of the team.'
        )
    ]

class TeamCreateUpdateBase(ConfiguredModel):
    """Schema for creating a team."""
    name: Annotated[
        str,
        Field(
            ...,
            title='Team Name',
            description='The name of the team.',
            max_length=250
        )
    ]
    mentor_id: Annotated[
        int,
        Field(
            ...,
            title='Mentor ID',
            description='The ID of the mentor who created the team.'
        )
    ]
    project_id: Annotated[
        Optional[int],
        Field(
            default=None,
            title='Project ID',
            description='The ID of the project that the team is associated with.'
        )
    ]
    team_members: Annotated[
        List[TeamMemberCreate],
        Field(
            ...,
            title='Team Members',
            description='The members of the team.'
        )
    ]

    @model_validator(mode='after')
    def validate_single_captain(self):
        captain_count = sum(
            1 for member in self.team_members 
            if member.role_name and 'капитан' in member.role_name.lower()
        )
        if captain_count > 1:
            raise ValueError("Team can have only one captain")
        return self

class TeamMemberUpdate(ConfiguredModel):
    """Schema for updating a team member."""
    role_name: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Role Name',
            description='The role of the participant in the team.',
            max_length=250
        )
    ]


class TeamInDB(CreatedUpdatedAt, TeamCreateUpdateBase):
    """Schema for a team to be returned."""
    id: Annotated[
        int,
        Field(
            title='Team ID',
            description='The ID of the team.'
        )
    ]


class TeamCreate(TeamCreateUpdateBase):
    """Schema for creating a team."""


class TeamUpdate(ConfiguredModel):
    """Schema for updating a team."""
    name: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Team Name',
            description='The name of the team.',
            max_length=250
        )
    ]
    mentor_id: Annotated[
        Optional[int],
        Field(
            default=None,
            title='Mentor ID',
            description='The ID of the mentor who created the team.'
        )
    ]
    project_id: Annotated[
        Optional[int],
        Field(
            default=None,
            title='Project ID',
            description='The ID of the project that the team is associated with.'
        )
    ]
    team_members: Annotated[
        Optional[List[TeamMemberCreate]],
        Field(
            default=None,
            title='Team Members',
            description='The members of the team.'
        )
    ]
