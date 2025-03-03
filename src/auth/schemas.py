from typing import Annotated
from pydantic import Field

from schemas import ConfiguredModel


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
