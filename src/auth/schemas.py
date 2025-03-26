from typing import Annotated

from pydantic import Field, field_validator

from schemas import ConfiguredModel
from utils import validate_password


class TokenOut(ConfiguredModel):
    """Login response schema."""
    access_token: Annotated[
        str, Field(
            ...,
            title='Access Token',
        )
    ]
    access_token_expire_minutes: Annotated[
        int, Field(
            ...,
            title='Access token expiration (in minutes)'
        )
    ]
    refresh_token: Annotated[
        str, Field(
            ...,
            title='Refresh token',
        )
    ]
    refresh_token_expire_minutes: Annotated[
        int, Field(
            ...,
            title='Refresh token expiration (in minutes)'
        )
    ]


class RefreshTokenInput(ConfiguredModel):
    refresh_token: Annotated[
        str, Field(
            ...,
            title='Refresh token'
        )
    ]


class NewPasswordInput(ConfiguredModel):
    new_password: Annotated[
        str, Field(
            ...,
            title='New password',
        )
    ]

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, new_password: str) -> str:
        validate_password(new_password)
        return new_password


class ChangePasswordInput(NewPasswordInput):
    old_password: Annotated[
        str, Field(
            ...,
            title='Old password',
        )
    ]
