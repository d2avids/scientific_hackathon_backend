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

    @field_validator('role_name')
    @classmethod
    def validate_role_format(cls, v):
        if v and not v.replace(' ', '').isalpha():
            raise ValueError('Role name can only contain letters and spaces')
        return v


class TeamMemberCreateUpdate(TeamMemberBase):
    """Schema for creating a team member."""


class TeamMemberInDB(CreatedUpdatedAt, TeamMemberBase, IDModel):
    """Schema for a team member to be returned."""


class TeamMentorID(ConfiguredModel):
    """Schema for a team mentor ID."""
    mentor_id: Annotated[
        int,
        Field(..., title='Mentor ID', description='The ID of the mentor who created the team.')
    ]


class TeamBase(ConfiguredModel):
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
    project_id: Annotated[
        Optional[int],
        Field(
            default=None,
            title='Project ID',
            description='The ID of the project that the team is associated with.'
        )
    ]

    @model_validator(mode='after')
    def validate_single_captain(self):
        captain_count = sum(
            1 for member in self.team_members
            if member.role_name and 'капитан' in member.role_name.lower()
        )
        if captain_count > 1:
            raise ValueError('Team can have only one captain')
        return self


class TeamCreateUpdate(TeamBase):
    """Schema for creating a team."""
    team_members: Annotated[
        List[TeamMemberCreateUpdate],
        Field(
            ...,
            title='Team Members',
            description='The members of the team.'
        )
    ]


class TeamInDB(CreatedUpdatedAt, TeamBase, TeamMentorID, IDModel):
    """Schema for a team to be returned."""
    team_members: Annotated[
        List[TeamMemberInDB],
        Field(..., title='Team Members', description='The members of the team.')
    ]
