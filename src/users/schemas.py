from datetime import date
from typing import Optional, Annotated
from urllib.parse import urljoin

from pydantic import Field, EmailStr, model_validator, field_serializer, field_validator, AliasPath

from schemas import ConfiguredModel, CreatedUpdatedAt, IDModel
from settings import settings
from utils import validate_password


class ParticipantBase(ConfiguredModel):
    region_id: Annotated[
        int,
        Field(
            ...,
            title='Region ID',
            description='Identifier for the participant\'s region.'
        )
    ]
    school_grade: Annotated[
        str,
        Field(
            ...,
            title='School Grade',
            description='Participant\'s current school grade.',
            max_length=15
        )
    ]
    city: Annotated[
        str,
        Field(
            ...,
            title='City',
            description='City where the participant resides.',
            max_length=250
        )
    ]


class MentorBase(ConfiguredModel):
    job_title: Annotated[
        str,
        Field(
            ...,
            title='Job Title',
            description='The mentor\'s job title.',
            max_length=150,
        )
    ]


class ParticipantCreate(ParticipantBase):
    """Schema for creating a participant."""


class MentorCreate(MentorBase):
    """Schema for creating a mentor."""


class ParticipantUpdate(ConfiguredModel):
    """Schema for updating a participant."""
    region_id: Annotated[
        Optional[int],
        Field(
            default=None,
            title='Region ID',
            description='Identifier for the participant\'s region.'
        )
    ]
    school_grade: Annotated[
        Optional[str],
        Field(
            default=None,
            title='School Grade',
            description='Participant\'s current school grade.',
            max_length=15
        )
    ]
    city: Annotated[
        Optional[str],
        Field(
            default=None,
            title='City',
            description='City where the participant resides.',
            max_length=150
        )
    ]
    interests: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Interests',
            max_length=250
        )
    ]
    olympics: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Olympics',
            max_length=250
        )
    ]
    achievements: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Achievements',
            max_length=250
        )
    ]


class MentorUpdate(MentorBase):
    """Schema for updating a mentor."""
    specialization: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Specialization',
            description='The mentor\'s area of specialization.',
            max_length=250,
        )
    ]
    job_title: Annotated[
        str,
        Field(
            default=None,
            title='Job Title',
            description='The mentor\'s job title.',
            max_length=150,
        )
    ]
    research_topics: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Research Topics',
            max_length=500,
        )
    ]
    articles: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Articles',
            max_length=500,
        )
    ]
    scientific_interests: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Scientific Interests',
            max_length=500,
        )
    ]
    taught_subjects: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Taught Subjects',
            max_length=500,
        )
    ]


class ParticipantInDB(CreatedUpdatedAt, ParticipantUpdate, IDModel):
    """Schema for a participant to be returned."""


class MentorInDB(CreatedUpdatedAt, MentorUpdate, IDModel):
    """Schema for a mentor to be returned."""
    is_admin: Annotated[
        bool,
        Field(title='Indicates whether the user is an admin', )
    ]


class UserBase(ConfiguredModel):
    first_name: Annotated[
        str,
        Field(
            ...,
            title='First Name',
            min_length=2,
            max_length=50
        )
    ]
    last_name: Annotated[
        str,
        Field(
            ...,
            title='Last Name',
            min_length=2,
            max_length=50
        )
    ]
    patronymic: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Patronymic',
            min_length=2,
            max_length=50
        )
    ]
    birth_date: Annotated[
        date,
        Field(
            ...,
            title='Birth Date',
            description='Participant\'s date of birth.'
        )
    ]
    phone_number: Annotated[
        str,
        Field(
            ...,
            title='Phone Number',
            description='Russian phone number in the format 7XXXXXXXXXX',
            pattern=r'^7\d{10}$'
        )
    ]
    edu_organization: Annotated[
        str,
        Field(
            ...,
            title='Educational Organization',
            max_length=100
        )
    ]


class UserCreateUpdateBase(UserBase):
    """Schema for creating a user."""
    participant: Annotated[
        Optional[ParticipantCreate],
        Field(
            default=None,
            title='Participant Details',
            description='Participant-specific details participant users.'
        )
    ]
    mentor: Annotated[
        Optional[MentorCreate],
        Field(
            default=None,
            title='Mentor Details',
            description='Mentor-specific details for mentor users.'
        )
    ]


class UserCreate(UserCreateUpdateBase):
    """Schema for creating a user."""
    email: Annotated[
        EmailStr,
        Field(
            ...,
            title='Email',
            description='Serves as login.',
            examples=['user@example.com']
        )
    ]
    password: Annotated[
        str,
        Field(
            ...,
            title='Password',
            min_length=8,
            max_length=32
        )
    ]
    is_mentor: Annotated[
        bool,
        Field(
            default=False,
            title='Is Mentor',
            description='Indicates whether the user is a mentor.',
        )
    ]
    personal_data: Annotated[
        bool,
        Field(
            default=True,
            title='Personal Data Agreement',
            description='User consent for processing personal data.'
        )
    ]
    regulations_agreement: Annotated[
        bool,
        Field(
            default=True,
            title='Regulations Agreement',
            description='User agreement to the platform\'s regulations.'
        )
    ]

    @field_validator('password')
    @classmethod
    def validate_password_value(cls, v: str) -> str:
        validate_password(v)
        return v

    @model_validator(mode='after')
    @classmethod
    def check_role_details(cls, instance: 'UserCreate') -> 'UserCreate':
        if instance.is_mentor:
            if instance.mentor is None:
                raise ValueError('Mentor details must be provided for mentor user')
        else:
            if instance.participant is None:
                raise ValueError('Participant details must be provided for non-mentor user')
        return instance


class UserUpdate(ConfiguredModel):
    first_name: Annotated[
        Optional[str],
        Field(
            default=None,
            title='First Name',
            min_length=2,
            max_length=50
        )
    ]
    last_name: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Last Name',
            min_length=2,
            max_length=50
        )
    ]
    patronymic: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Patronymic',
            min_length=2,
            max_length=50
        )
    ]
    phone_number: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Phone Number',
            description='Russian phone number in the format 7XXXXXXXXXX',
            pattern=r'^7\d{10}$'
        )
    ]
    about: Annotated[
        Optional[str],
        Field(
            default=None,
            title='About',
            max_length=2500,
        )
    ]
    edu_organization: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Educational Organization',
            max_length=100
        )
    ]
    participant: Annotated[
        Optional[ParticipantUpdate], Field(
            default=None,
            title='Participant Instance'
        )
    ]
    mentor: Annotated[
        Optional[MentorUpdate], Field(
            default=None,
            title='Mentor instance'
        )
    ]

    @model_validator(mode="before")
    @classmethod
    def check_explicit_null_fields(cls, values):
        fields_cant_be_none_if_present = [
            'firstName',
            'lastName',
            'phoneNumber',
            'birthDate',
            'eduOrganization',
            'mentor',
            'participant'
        ]
        for field_name in fields_cant_be_none_if_present:
            if field_name in values and not values[field_name]:
                raise ValueError(f'{field_name} cannot be null if explicitly passed')

        return values


class UserInDB(UserBase, CreatedUpdatedAt, IDModel):
    """Schema for a user to be returned."""
    email: Annotated[
        EmailStr,
        Field(
            ...,
            title='Email',
            description='Serves as login.',
            examples=['user@example.com']
        )
    ]
    is_mentor: Annotated[
        bool,
        Field(
            default=False,
            title='Is Mentor',
            description='Indicates whether the user is a mentor.',
        )
    ]
    participant: Annotated[
        Optional[ParticipantInDB], Field(
            default=None,
            title='Participant Instance'
        )
    ]
    mentor: Annotated[
        Optional[MentorInDB], Field(
            default=None,
            title='Mentor instance'
        )
    ]
    verified: Annotated[
        bool,
        Field(
            title='Verified',
            description='Indicates whether the user is verified.'
        )
    ]
    photo_path: Annotated[Optional[str], Field(title='Photo file path', )]

    @field_serializer('photo_path')
    def _photo_path_serializer(self, photo_path: Optional[str]) -> Optional[str]:
        """Generates url path to the file."""
        if photo_path is None:
            return None
        return urljoin(settings.SERVER_URL, photo_path)


class UserInDBWithTeamID(UserInDB):
    team_id: Annotated[
        Optional[int],
        Field(
            title='Team ID',
            validation_alias=AliasPath('participant', 'team_members', 'team_id')
        )
    ]


class UserDocumentBase(ConfiguredModel):
    name: Annotated[str, Field(title='File name', )]
    path: Annotated[str, Field(title='File path', )]
    size: Annotated[float, Field(title='File size', description='File size represented in bytes', )]
    mimetype: Annotated[str, Field(title='File mimetype', )]


class FileCreate(ConfiguredModel):
    path: Annotated[str, Field(title='File path', )]


class UserDocumentInDB(CreatedUpdatedAt, UserDocumentBase, IDModel):
    @field_serializer('path')
    def _path_serializer(self, path: Optional[str]) -> Optional[str]:
        """Generates url path to the file."""
        if path is None:
            return None
        return urljoin(settings.SERVER_URL, path)


class RegionInDB(ConfiguredModel, IDModel):
    name: Annotated[
        str,
        Field(
            title='Region name',
            max_length=250,
        )
    ]
    code: Annotated[
        Optional[int],
        Field(
            default=None,
            title='Region code',
        )
    ]


class ShortUserInDB(ConfiguredModel, IDModel):
    first_name: Annotated[
        str,
        Field(
            ...,
            title='First Name',
            min_length=2,
            max_length=50
        )
    ]
    last_name: Annotated[
        str,
        Field(
            ...,
            title='Last Name',
            min_length=2,
            max_length=50
        )
    ]
    patronymic: Annotated[
        Optional[str],
        Field(
            default=None,
            title='Patronymic',
            min_length=2,
            max_length=50
        )
    ]
    is_mentor: Annotated[
        bool,
        Field(
            default=False,
            title='Is Mentor',
            description='Indicates whether the user is a mentor.',
        )
    ]
