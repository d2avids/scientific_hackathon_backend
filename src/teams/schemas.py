from typing import Annotated, List, Optional

from pydantic import Field, field_validator, model_validator

from schemas import ConfiguredModel, CreatedUpdatedAt, IDModel


class TeamMemberBase(ConfiguredModel):
    """Schema for a team member to be returned."""
    participant_id: Annotated[
        int,
        Field(
            ...,
            title='Participant ID',
            description='The ID of the participant who is a member of the team.'
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


class TeamMemberCreateUpdate(TeamMemberBase):
    """Schema for creating a team member."""

    @field_validator('role_name')
    @classmethod
    def validate_role_format(cls, v):
        if v and not v.replace(' ', '').isalpha():
            raise ValueError('Role name can only contain letters and spaces')
        return v


class TeamMemberInDB(CreatedUpdatedAt, TeamMemberBase, IDModel):
    """Schema for a team member to be returned."""


class TeamMentorID(ConfiguredModel):
    """Schema for a team mentor ID."""
    mentor_id: Annotated[
        int,
        Field(..., title='Mentor ID', description='The ID of the mentor who created the team.')
    ]


class TeamBase(ConfiguredModel):
    """Base schema for a team."""

    @model_validator(mode='after')
    def validate_single_captain(self):
        if self.team_members:
            captain_count = sum(
                1 for member in self.team_members
                if member.role_name and 'капитан' in member.role_name.lower()
            )
            if captain_count > 1:
                raise ValueError('Team can have only one captain')
        return self


class TeamCreate(TeamBase):
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
    team_members: Annotated[
        Optional[List[TeamMemberCreateUpdate]],
        Field(
            default=None,
            title='Team Members',
            description='The members of the team.'
        )
    ]


class TeamUpdate(TeamBase):
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
    project_id: Annotated[
        Optional[int],
        Field(
            default=None,
            title='Project ID',
            description='The ID of the project that the team is associated with.'
        )
    ]
    team_members: Annotated[
        Optional[List[TeamMemberCreateUpdate]],
        Field(
            default=None,
            title='Team Members',
            description='The members of the team.'
        )
    ]


class TeamInDB(TeamMentorID, CreatedUpdatedAt, ConfiguredModel, IDModel):
    """Schema for a team to be returned."""
    name: Annotated[
        str,
        Field(
            ...,
            title='Team Name',
            description='The name of the team.',
            max_length=250
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
        List[TeamMemberInDB],
        Field(..., title='Team Members', description='The members of the team.')
    ]
